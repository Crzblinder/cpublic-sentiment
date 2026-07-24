"""爬虫模块测试。

测试内容：
- RawNewsItem 数据类格式正确性
- 数据源配置完整性
- RSS 解析正确性（mock feedparser 输入）
- API 解析与字段映射
- 单源失败隔离（不影响其他源）
- 每源采集条数上限
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sentiment.db")
os.environ.setdefault("VECTOR_DB_PATH", "./test_chroma_data")

from app.crawler.scraper import BROWSER_UA, MAX_ITEMS_PER_SOURCE, NewsScraper, RawNewsItem, get_status
from app.crawler.sources import SOURCES


# ------------------------------------------------------------------
# RawNewsItem 数据类测试
# ------------------------------------------------------------------

class TestRawNewsItem:
    """测试 RawNewsItem dataclass 字段完整性。"""

    def test_all_fields(self):
        """测试所有字段正确赋值。"""
        item = RawNewsItem(
            title="测试标题",
            content="测试内容",
            source_name="test_source",
            url="https://example.com/test",
            published_at="2024-01-01",
        )
        assert item.title == "测试标题"
        assert item.content == "测试内容"
        assert item.source_name == "test_source"
        assert item.url == "https://example.com/test"
        assert item.published_at == "2024-01-01"

    def test_default_published_at(self):
        """测试 published_at 默认值为空字符串。"""
        item = RawNewsItem(
            title="测试标题",
            content="测试内容",
            source_name="test_source",
            url="https://example.com/test",
        )
        assert item.published_at == ""

    def test_field_types(self):
        """测试字段类型为 str。"""
        item = RawNewsItem(
            title="标题",
            content="内容",
            source_name="src",
            url="url",
            published_at="date",
        )
        assert isinstance(item.title, str)
        assert isinstance(item.content, str)
        assert isinstance(item.source_name, str)
        assert isinstance(item.url, str)
        assert isinstance(item.published_at, str)


# ------------------------------------------------------------------
# 数据源配置测试
# ------------------------------------------------------------------

class TestSourcesConfig:
    """测试数据源配置完整性。"""

    def test_source_count(self):
        """测试数据源数量为 5 个。"""
        assert len(SOURCES) == 5

    def test_source_fields(self):
        """测试每个源包含必需字段。"""
        required_fields = {"name", "type", "url", "parser", "description"}
        for source in SOURCES:
            assert required_fields.issubset(source.keys()), f"源 {source.get('name')} 缺少字段"

    def test_source_names_snake_case(self):
        """测试数据源名称为 snake_case 格式。"""
        expected_names = {"chinanews_rss", "people_rss", "xinhua_rss", "36kr_api", "cls_api"}
        actual_names = {s["name"] for s in SOURCES}
        assert actual_names == expected_names

    def test_api_sources_have_fields_map(self):
        """测试 API 类型数据源包含 fields_map。"""
        for source in SOURCES:
            if source["parser"] == "json_api":
                assert "fields_map" in source, f"API 源 {source['name']} 缺少 fields_map"
                fm = source["fields_map"]
                assert "title" in fm
                assert "content" in fm
                assert "url" in fm
                assert "published_at" in fm

    def test_parser_types(self):
        """测试 parser 类型仅限于 feedparser 和 json_api。"""
        for source in SOURCES:
            assert source["parser"] in ("feedparser", "json_api")


# ------------------------------------------------------------------
# RSS 解析测试
# ------------------------------------------------------------------

class TestRSSParsing:
    """测试 RSS 解析正确性。"""

    def test_parse_rss_basic(self):
        """测试 RSS 基本解析：提取 title/content/url/published_at。"""
        scraper = NewsScraper()
        rss_content = ("""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
        <channel>
            <title>测试 RSS</title>
            <item>
                <title>第一条新闻标题</title>
                <link>https://example.com/news/1</link>
                <description>第一条新闻的摘要内容</description>
                <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
            </item>
            <item>
                <title>第二条新闻标题</title>
                <link>https://example.com/news/2</link>
                <description>第二条新闻的摘要内容</description>
                <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
            </item>
        </channel>
        </rss>""").encode("utf-8")

        source = SOURCES[0]  # chinanews_rss
        items = scraper._parse_rss(rss_content, source)

        assert len(items) == 2
        assert items[0].title == "第一条新闻标题"
        assert items[0].content == "第一条新闻的摘要内容"
        assert items[0].url == "https://example.com/news/1"
        assert items[0].source_name == "chinanews_rss"
        assert items[0].published_at == "Mon, 01 Jan 2024 00:00:00 GMT"

    def test_parse_rss_empty_feed(self):
        """测试空 RSS 源返回空列表。"""
        scraper = NewsScraper()
        rss_content = ("""<?xml version="1.0"?>
        <rss><channel><title>空</title></channel></rss>""").encode("utf-8")
        source = SOURCES[0]
        items = scraper._parse_rss(rss_content, source)
        assert len(items) == 0

    def test_parse_rss_missing_fields(self):
        """测试 RSS 条目缺失部分字段时的容错处理。"""
        scraper = NewsScraper()
        rss_content = ("""<?xml version="1.0"?>
        <rss><channel>
        <item>
            <title>只有标题的新闻</title>
        </item>
        </channel></rss>""").encode("utf-8")
        source = SOURCES[0]
        items = scraper._parse_rss(rss_content, source)
        assert len(items) == 1
        assert items[0].title == "只有标题的新闻"
        # 缺失 content 时回退到 title
        assert items[0].content == "只有标题的新闻"

    def test_parse_rss_max_items(self):
        """测试每源最多采集 30 条限制。"""
        scraper = NewsScraper()
        # 构造 35 条 RSS 条目
        items_xml = "<?xml version='1.0'?><rss><channel>"
        for i in range(35):
            items_xml += f"""
            <item>
                <title>新闻标题{i}</title>
                <link>https://example.com/news/{i}</link>
                <description>内容{i}</description>
            </item>"""
        items_xml += "</channel></rss>"

        source = SOURCES[0]
        items = scraper._parse_rss(items_xml.encode(), source)
        assert len(items) == MAX_ITEMS_PER_SOURCE  # 30


# ------------------------------------------------------------------
# API 解析测试
# ------------------------------------------------------------------

class TestAPIParsing:
    """测试 JSON API 解析与字段映射。"""

    def test_parse_api_36kr(self):
        """测试 36kr API 解析与 fields_map 映射。"""
        scraper = NewsScraper()
        mock_json = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "title": "36氪快讯标题",
                        "summary": "快讯摘要内容",
                        "news_url": "https://36kr.com/news/1",
                        "published_at": "2024-01-01 10:00:00",
                    },
                    {
                        "title": "第二条快讯",
                        "summary": "第二条摘要",
                        "news_url": "https://36kr.com/news/2",
                        "published_at": "2024-01-01 11:00:00",
                    },
                ]
            },
        }

        source_36kr = next(s for s in SOURCES if s["name"] == "36kr_api")
        items = scraper._parse_api(mock_json, source_36kr)

        assert len(items) == 2
        assert items[0].title == "36氪快讯标题"
        assert items[0].content == "快讯摘要内容"
        assert items[0].url == "https://36kr.com/news/1"
        assert items[0].source_name == "36kr_api"
        assert items[0].published_at == "2024-01-01 10:00:00"

    def test_parse_api_cls(self):
        """测试财联社 API 解析（含时间戳 published_at）。"""
        scraper = NewsScraper()
        mock_json = {
            "data": {
                "roll_data": [
                    {
                        "title": "财联社电报标题",
                        "content": "电报内容详情",
                        "shareurl": "https://www.cls.cn/detail/1",
                        "ctime": 1704067200,
                    },
                ]
            }
        }

        source_cls = next(s for s in SOURCES if s["name"] == "cls_api")
        items = scraper._parse_api(mock_json, source_cls)

        assert len(items) == 1
        assert items[0].title == "财联社电报标题"
        assert items[0].content == "电报内容详情"
        assert items[0].url == "https://www.cls.cn/detail/1"
        assert items[0].source_name == "cls_api"
        assert items[0].published_at == "1704067200"  # 转为字符串

    def test_parse_api_empty(self):
        """测试空 API 响应返回空列表。"""
        scraper = NewsScraper()
        source = next(s for s in SOURCES if s["name"] == "36kr_api")
        items = scraper._parse_api({}, source)
        assert len(items) == 0

    def test_extract_items_list_nested(self):
        """测试从嵌套 JSON 中提取列表。"""
        scraper = NewsScraper()
        # 测试 data.items 嵌套结构
        data = {"data": {"items": [{"a": 1}, {"b": 2}]}}
        result = scraper._extract_items_list(data)
        assert len(result) == 2

        # 测试 data.roll_data 嵌套结构
        data = {"data": {"roll_data": [{"a": 1}]}}
        result = scraper._extract_items_list(data)
        assert len(result) == 1

        # 测试顶层列表
        data = [{"a": 1}]
        result = scraper._extract_items_list(data)
        assert len(result) == 1


# ------------------------------------------------------------------
# 单源失败隔离测试
# ------------------------------------------------------------------

class TestSourceFailureIsolation:
    """测试单源失败不影响其他源采集。"""

    def test_single_source_timeout_isolation(self):
        """测试一个源超时不会中断其他源采集。"""
        scraper = NewsScraper()

        # 模拟 _fetch_source：chinanews_rss 超时，其他源正常返回
        async def mock_fetch_source(client, source):
            if source["name"] == "chinanews_rss":
                raise httpx.TimeoutException("Connection timed out")
            return [
                RawNewsItem(
                    title=f"来自{source['name']}的新闻",
                    content="测试内容",
                    source_name=source["name"],
                    url=f"https://example.com/{source['name']}/1",
                )
            ]

        with patch.object(scraper, "_fetch_source", mock_fetch_source):
            items = asyncio.run(scraper.fetch_all())

        status = get_status()

        # chinanews_rss 应在失败列表中
        assert "chinanews_rss" in status["sources_failed"]
        # 其他 4 个源应该成功
        assert len(status["sources_ok"]) == 4
        # 应该有数据返回（来自非 chinanews 源）
        assert len(items) >= 4
        # 所有返回的数据不包含 chinanews_rss 的
        for item in items:
            assert item.source_name != "chinanews_rss"

    def test_all_sources_failure(self):
        """测试所有源都失败时返回空列表且状态正确。"""
        scraper = NewsScraper()

        async def mock_fetch_source(client, source):
            raise httpx.ConnectError("Connection refused")

        with patch.object(scraper, "_fetch_source", mock_fetch_source):
            items = asyncio.run(scraper.fetch_all())

        status = get_status()
        assert len(items) == 0
        assert len(status["sources_failed"]) == 5
        assert len(status["sources_ok"]) == 0

    def test_sources_detail_tracking(self):
        """测试 sources_detail 正确跟踪每个源的采集数和状态。"""
        scraper = NewsScraper()

        async def mock_fetch_source(client, source):
            if source["name"] == "people_rss":
                raise httpx.TimeoutException("timeout")
            return [
                RawNewsItem(title="标题1", content="内容", source_name=source["name"], url="url1"),
                RawNewsItem(title="标题2", content="内容", source_name=source["name"], url="url2"),
            ]

        with patch.object(scraper, "_fetch_source", mock_fetch_source):
            asyncio.run(scraper.fetch_all())

        status = get_status()
        assert "sources_detail" in status
        details = status["sources_detail"]
        assert len(details) == 5

        for detail in details:
            if detail["name"] == "people_rss":
                assert detail["ok"] is False
                assert detail["count"] == 0
            else:
                assert detail["ok"] is True
                assert detail["count"] == 2
