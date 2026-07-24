"""舆情新闻爬虫核心模块。

使用 httpx.AsyncClient 并发采集多个数据源：
- RSS 源通过 feedparser 解析
- API 源通过 JSON 解析 + fields_map 字段映射

所有错误仅记录日志不抛出异常，单源失败不影响其他源。
采集结果为 RawNewsItem 列表，可直接送入 CleaningPipeline 清洗。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from app.crawler.sources import SOURCES

logger = logging.getLogger(__name__)

# 正常浏览器 User-Agent
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 每个源最多采集的条目数
MAX_ITEMS_PER_SOURCE = 30

# 爬虫状态（全局单例）
_last_run_status: dict[str, Any] = {
    "last_run": None,
    "total_fetched": 0,
    "sources_ok": [],
    "sources_failed": [],
    "sources_detail": [],
}


def get_status() -> dict[str, Any]:
    """返回爬虫最近一次运行状态。"""
    return _last_run_status.copy()


@dataclass
class RawNewsItem:
    """爬虫采集到的原始新闻条目。"""

    title: str
    content: str
    source_name: str
    url: str
    published_at: str = ""


class NewsScraper:
    """公开新闻源爬虫，并发采集后返回统一格式的 RawNewsItem 列表。"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch_all(self) -> list[RawNewsItem]:
        """并发遍历所有数据源进行采集，返回统一格式的新闻列表。

        单源失败仅记录到 sources_failed，不影响其他源。
        """
        all_items: list[RawNewsItem] = []
        sources_ok: list[str] = []
        sources_failed: list[str] = []
        sources_detail: list[dict[str, Any]] = []

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": BROWSER_UA},
        ) as client:
            # 并发采集所有源，单源 try/except 隔离
            tasks = [self._fetch_source_safe(client, source) for source in SOURCES]
            results = await asyncio.gather(*tasks)

        for source_name, items, success in results:
            if success and items:
                all_items.extend(items)
                sources_ok.append(source_name)
                sources_detail.append({
                    "name": source_name,
                    "count": len(items),
                    "ok": True,
                })
                logger.info("源 %s 采集到 %d 条", source_name, len(items))
            else:
                sources_failed.append(source_name)
                sources_detail.append({
                    "name": source_name,
                    "count": 0,
                    "ok": False,
                })

        # 更新全局状态
        _last_run_status["last_run"] = datetime.now(UTC).isoformat()
        _last_run_status["total_fetched"] = len(all_items)
        _last_run_status["sources_ok"] = sources_ok
        _last_run_status["sources_failed"] = sources_failed
        _last_run_status["sources_detail"] = sources_detail

        return all_items

    async def _fetch_source_safe(
        self, client: httpx.AsyncClient, source: dict[str, Any]
    ) -> tuple[str, list[RawNewsItem], bool]:
        """安全采集单个数据源，异常时返回空列表和失败标记。

        Returns:
            (source_name, items, success)
        """
        try:
            items = await self._fetch_source(client, source)
            return (source["name"], items, True)
        except Exception as e:
            logger.warning("源 %s 采集失败: %s", source["name"], e)
            return (source["name"], [], False)

    async def _fetch_source(
        self, client: httpx.AsyncClient, source: dict[str, Any]
    ) -> list[RawNewsItem]:
        """根据数据源类型分发采集并解析。"""
        resp = await client.get(source["url"])
        resp.raise_for_status()

        if source["parser"] == "feedparser":
            return self._parse_rss(resp.content, source)
        elif source["parser"] == "json_api":
            return self._parse_api(resp.json(), source)
        return []

    def _parse_rss(
        self, content_bytes: bytes, source: dict[str, Any]
    ) -> list[RawNewsItem]:
        """使用 feedparser 解析 RSS/Atom 格式响应。

        Args:
            content_bytes: HTTP 响应原始字节
            source: 数据源配置字典

        Returns:
            解析后的 RawNewsItem 列表（最多 MAX_ITEMS_PER_SOURCE 条）
        """
        feed = feedparser.parse(content_bytes)
        items: list[RawNewsItem] = []

        for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
            title = getattr(entry, "title", "") or ""
            content = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or title
            )
            url = getattr(entry, "link", "") or ""
            published_at = (
                getattr(entry, "published", "")
                or getattr(entry, "updated", "")
                or ""
            )

            if not title:
                continue

            items.append(RawNewsItem(
                title=title.strip(),
                content=content.strip(),
                source_name=source["name"],
                url=url.strip(),
                published_at=published_at.strip(),
            ))

        return items

    def _parse_api(
        self, resp_json: dict[str, Any], source: dict[str, Any]
    ) -> list[RawNewsItem]:
        """使用 fields_map 字段映射解析 JSON API 响应。

        Args:
            resp_json: HTTP 响应解析后的 JSON 字典
            source: 数据源配置字典（含 fields_map）

        Returns:
            解析后的 RawNewsItem 列表（最多 MAX_ITEMS_PER_SOURCE 条）
        """
        fields_map = source.get("fields_map", {})
        items_list = self._extract_items_list(resp_json)

        items: list[RawNewsItem] = []
        for raw_item in items_list[:MAX_ITEMS_PER_SOURCE]:
            if not isinstance(raw_item, dict):
                continue

            title = str(raw_item.get(fields_map.get("title", "title"), "") or "")
            content = str(raw_item.get(fields_map.get("content", "content"), "") or "")
            url = str(raw_item.get(fields_map.get("url", "url"), "") or "")
            published_at = raw_item.get(fields_map.get("published_at", "published_at"), "")

            # 处理时间戳格式的 published_at
            if isinstance(published_at, (int, float)):
                published_at = str(published_at)
            else:
                published_at = str(published_at or "")

            if not title and not content:
                continue

            items.append(RawNewsItem(
                title=title.strip() or (content[:80].strip() if content else ""),
                content=content.strip() or title.strip(),
                source_name=source["name"],
                url=url.strip(),
                published_at=published_at.strip(),
            ))

        return items

    def _extract_items_list(self, data: Any) -> list[dict[str, Any]]:
        """从 JSON API 响应中递归提取新闻条目列表。

        尝试常见嵌套结构（data.items, data.list, data.roll_data 等），
        若未命中则回退到深度优先搜索第一个 dict 列表。
        """
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []

        # 第一层：尝试常见列表字段
        for key in ("data", "items", "list", "results"):
            val = data.get(key)
            if isinstance(val, list):
                return val

        # 第二层：data 是 dict，尝试子级常见列表字段
        data_node = data.get("data")
        if isinstance(data_node, dict):
            for sub_key in ("items", "list", "roll_data", "newsflashList",
                            "data", "results", "feeds"):
                sub_val = data_node.get(sub_key)
                if isinstance(sub_val, list):
                    return sub_val

        # 回退：深度优先搜索第一个包含 dict 的列表
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
            if isinstance(v, dict):
                for sub_v in v.values():
                    if isinstance(sub_v, list) and sub_v and isinstance(sub_v[0], dict):
                        return sub_v

        return []
