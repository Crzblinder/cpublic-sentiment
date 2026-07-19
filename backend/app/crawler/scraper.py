"""舆情新闻爬虫核心模块。

支持多种数据源采集，所有错误仅记录日志不抛出异常。
采集到的文本可直接送入 SentimentService.analyze() 进行分析。
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.crawler.sources import SOURCES

logger = logging.getLogger(__name__)

# 爬虫状态（全局单例）
_last_run_status: dict[str, Any] = {
    "last_run": None,
    "total_fetched": 0,
    "sources_ok": [],
    "sources_failed": [],
}


def get_status() -> dict[str, Any]:
    """返回爬虫最近一次运行状态。"""
    return _last_run_status.copy()


class NewsScraper:
    """公开新闻源爬虫，采集后返回结构化文本列表。"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def fetch_all(self) -> list[dict[str, Any]]:
        """遍历所有数据源进行采集，返回统一格式的新闻列表。"""
        all_items: list[dict[str, Any]] = []
        sources_ok: list[str] = []
        sources_failed: list[str] = []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for source in SOURCES:
                try:
                    items = await self._fetch_source(client, source)
                    if items:
                        all_items.extend(items)
                        sources_ok.append(source["name"])
                        logger.info("源 %s 采集到 %d 条", source["name"], len(items))
                    else:
                        sources_failed.append(source["name"])
                except Exception as e:
                    sources_failed.append(source["name"])
                    logger.warning("源 %s 采集失败: %s", source["name"], e)

        _last_run_status["last_run"] = datetime.now(timezone.utc).isoformat()
        _last_run_status["total_fetched"] = len(all_items)
        _last_run_status["sources_ok"] = sources_ok
        _last_run_status["sources_failed"] = sources_failed

        return all_items

    async def _fetch_source(
        self, client: httpx.AsyncClient, source: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """根据数据源类型分发采集。"""
        resp = await client.get(source["url"], headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        resp.raise_for_status()

        if source["parser"] == "json_api":
            return self._parse_json_api(resp, source)
        elif source["parser"] == "html_parse":
            return self._parse_html(resp, source)
        return []

    def _parse_json_api(
        self, resp: httpx.Response, source: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """解析 JSON API 格式响应。"""
        try:
            data = resp.json()
        except Exception:
            return []

        items: list[dict[str, Any]] = []

        # 新浪财经格式
        if "result" in data and "data" in data.get("result", {}):
            for item in data["result"]["data"][:20]:
                title = item.get("title", "")
                content = item.get("intro", item.get("summary", title))
                if title:
                    items.append({
                        "title": title,
                        "content": content or title,
                        "source": source["name"],
                        "url": item.get("url", ""),
                        "published_at": item.get("ctime", ""),
                    })

        # 财联社格式
        elif "data" in data:
            for item in (data.get("data", {}).get("roll_data", []) or data.get("data", []))[:20]:
                title = item.get("title", "")
                content = item.get("content", item.get("brief", title))
                if title or content:
                    items.append({
                        "title": title or content[:80],
                        "content": content or title,
                        "source": source["name"],
                        "url": item.get("shareurl", ""),
                        "published_at": item.get("ctime", ""),
                    })

        return items

    def _parse_html(
        self, resp: httpx.Response, source: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """解析 HTML 页面。"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("bs4 not installed; skipping HTML parsing")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[dict[str, Any]] = []

        # 通用提取：找所有包含新闻文本的块
        for el in soup.select("article, .news-item, .flash-item, .article-item, [class*='news'], [class*='flash']"):
            title_el = el.find(["h1", "h2", "h3", "h4", "a"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            content = el.get_text(strip=True)
            if len(title) > 5 and len(content) > 10:
                items.append({
                    "title": title[:120],
                    "content": content[:500],
                    "source": source["name"],
                    "url": "",
                    "published_at": "",
                })
            if len(items) >= 20:
                break

        return items
