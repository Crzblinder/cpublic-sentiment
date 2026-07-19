import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sentiment.db")
os.environ.setdefault("VECTOR_DB_PATH", "./test_chroma_data")

from app.main import app
from app.models.base import Base, get_db

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
