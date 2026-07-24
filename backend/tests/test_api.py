import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sentiment.db")
os.environ.setdefault("VECTOR_DB_PATH", "./test_chroma_data")

from app.crawler.scraper import RawNewsItem
from app.main import app
from app.models.base import Base, get_db
from app.models.case import RiskCase

# Clean test artifacts before run
for p in [Path("./test_sentiment.db"), Path("./test_chroma_data")]:
    if p.exists():
        if p.is_file():
            p.unlink()
        else:
            import shutil
            shutil.rmtree(p, ignore_errors=True)

engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_without_data():
    # With empty DB, fallback deterministic behavior should still work
    response = client.post(
        "/api/v1/sentiment/analyze",
        json={"text": "某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "governance" in data


def test_cases_endpoint_empty():
    response = client.get("/api/v1/cases")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ------------------------------------------------------------------
# 新增测试：爬虫运行 + 空数据库友好响应 + 全文搜索
# ------------------------------------------------------------------

def test_crawler_run_with_mock_data():
    """测试 /crawler/run 端点（mock 爬虫返回固定数据）。"""
    mock_items = [
        RawNewsItem(
            title="某科技公司因数据泄露被监管部门处罚",
            content=(
                "某科技有限公司因用户数据泄露被监管部门立案处罚，"
                "黑客窃取了大量用户隐私信息，涉嫌严重违规操作。"
            ),
            source_name="test_source",
            url="https://example.com/test/crawler/1",
            published_at="2024-01-01",
        ),
    ]

    mock_scraper_instance = MagicMock()
    mock_scraper_instance.fetch_all = AsyncMock(return_value=mock_items)

    with patch("app.api.routes.NewsScraper", return_value=mock_scraper_instance):
        response = client.post("/api/v1/crawler/run")

    assert response.status_code == 200
    data = response.json()
    assert data["fetched"] == 1
    assert data["cleaned"] >= 1
    assert "persisted" in data
    assert "deduped" in data
    assert "analyzed" in data
    assert "status" in data
    assert isinstance(data["status"], dict)


def test_crawler_run_deduplication():
    """测试 /crawler/run 增量去重：重复运行相同数据时 deduped 增加。"""
    mock_items = [
        RawNewsItem(
            title="某银行因金融违规收到证监会罚单",
            content="某银行因金融违规操纵股价被证监会处罚，涉嫌内幕交易。",
            source_name="test_source",
            url="https://example.com/test/crawler/dedup",
            published_at="2024-01-01",
        ),
    ]

    mock_scraper_instance = MagicMock()
    mock_scraper_instance.fetch_all = AsyncMock(return_value=mock_items)

    with patch("app.api.routes.NewsScraper", return_value=mock_scraper_instance):
        # 第一次运行：应该持久化
        response1 = client.post("/api/v1/crawler/run")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["persisted"] >= 1

        # 第二次运行：相同数据应该被去重
        response2 = client.post("/api/v1/crawler/run")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["deduped"] >= 1


def test_empty_db_enterprises_endpoint():
    """测试空数据库时 /enterprises 返回友好响应。"""
    response = client.get("/api/v1/enterprises")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_empty_db_dashboard_stats():
    """测试空数据库时 /dashboard/stats 返回友好响应。"""
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data


def test_empty_db_events_endpoint():
    """测试空数据库时 /sentiment/events 返回空列表。"""
    response = client.get("/api/v1/sentiment/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_empty_db_crawler_status():
    """测试空数据库时 /crawler/status 返回友好响应。"""
    response = client.get("/api/v1/crawler/status")
    assert response.status_code == 200
    data = response.json()
    assert "last_run" in data
    assert "total_fetched" in data
    assert "sources_ok" in data
    assert "sources_failed" in data


def test_cases_full_text_search():
    """测试 /cases 搜索支持标题和摘要全文检索。"""
    # 创建一个案例：标题不含搜索词，但摘要包含
    db_session = TestingSessionLocal()
    try:
        case = RiskCase(
            title="某企业年度合规报告摘要",
            summary="该企业因食品安全问题被处罚，涉及食品过期和农药残留超标",
            industry="食品餐饮",
            risk_type="食品安全",
            risk_level="高",
            source_url="https://example.com/test/search",
        )
        db_session.add(case)
        db_session.commit()
    finally:
        db_session.close()

    # 搜索摘要中的关键词（标题中不包含此词）
    response = client.get("/api/v1/cases?search=农药残留")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("食品安全" == item["risk_type"] for item in data["items"])

    # 清理测试数据
    db_session = TestingSessionLocal()
    try:
        db_session.query(RiskCase).filter(RiskCase.source_url == "https://example.com/test/search").delete()
        db_session.commit()
    finally:
        db_session.close()


def test_events_include_source_field():
    """测试 /sentiment/events 响应包含 source 字段。"""
    response = client.get("/api/v1/sentiment/events")
    assert response.status_code == 200
    events = response.json()
    for event in events:
        assert "source" in event
