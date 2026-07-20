"""新版 Agent 单元测试：覆盖岗位技能图谱与人才匹配引擎的 5 个核心 Agent。

测试默认在无 LLM Key 的环境下运行，依赖内置的确定性降级规则引擎。
"""
# ruff: noqa: E402

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["OPENAI_API_KEY"] = ""
os.environ["DATABASE_URL"] = "sqlite:///./test_agents.db"
os.environ["VECTOR_DB_PATH"] = "./test_agents_chroma"

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.agents.jd_parser import JDParser
from app.agents.learning_planner import LearningPlanner
from app.agents.skill_advisor import SkillAdvisor
from app.agents.talent_matcher import TalentMatcher
from app.agents.trend_predictor import TrendPredictor
from app.agents.workflow import build_job_match_graph
from app.models import Company, Job
from app.models.base import Base

# 清理测试产物
for p in [Path("./test_agents.db"), Path("./test_agents_chroma")]:
    if p.exists():
        if p.is_file():
            p.unlink()
        else:
            import shutil

            shutil.rmtree(p, ignore_errors=True)

engine = create_engine(
    os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="module")
def db_session():
    """提供绑定到测试数据库的 Session。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_job(session, title: str, required_skills: list[str], description: str = "") -> Job:
    """构造一个测试岗位并持久化。"""
    company = session.query(Company).filter_by(name="示例科技").first()
    if company is None:
        company = Company(
            name="示例科技",
            industry="互联网",
            size="100-499人",
            city="北京",
        )
        session.add(company)
        session.flush()

    job = Job(
        title=title,
        company_id=company.id,
        city="北京",
        salary_min=20000,
        salary_max=35000,
        experience_level="3-5年",
        education_level="本科",
        required_skills=json.dumps(required_skills, ensure_ascii=False),
        description=description or f"招聘 {title}，要求掌握 {', '.join(required_skills)}。",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_jd_parser():
    agent = JDParser()
    jd_text = (
        "某科技公司招聘 Python 后端工程师\n"
        "岗位职责：负责后端服务开发。\n"
        "岗位要求：熟悉 Python、FastAPI、PostgreSQL，3-5 年经验，本科及以上学历。"
    )
    result = agent.parse_jd(jd_text)

    assert result["title"]
    assert "Python" in result["required_skills"]
    assert result["experience_level"] in ("3-5年", "不限")
    assert result["education_level"] in ("本科", "不限")


def test_talent_matcher(db_session):
    job = _make_job(
        db_session,
        title="Python 后端工程师",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    agent = TalentMatcher()
    result = agent.match(["Python", "FastAPI"], job, db_session)

    assert 0.0 <= result["match_score"] <= 1.0
    assert "Python" in result["matched_skills"]
    assert "FastAPI" in result["matched_skills"]
    assert "PostgreSQL" in result["missing_skills"]
    assert isinstance(result["analysis_summary"], str)


def test_trend_predictor():
    agent = TrendPredictor()
    job_data = [
        {
            "title": "Python 后端工程师",
            "city": "北京",
            "salary_min": 20000,
            "salary_max": 35000,
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
        },
        {
            "title": "Java 后端工程师",
            "city": "上海",
            "salary_min": 22000,
            "salary_max": 38000,
            "required_skills": ["Java", "Spring Boot", "MySQL"],
        },
    ]
    result = agent.predict(job_data)

    assert "summary" in result
    assert result["key_metrics"]["job_count"] == 2
    assert isinstance(result["top_skills"], list)
    assert isinstance(result["hot_job_titles"], list)


def test_learning_planner(db_session):
    agent = LearningPlanner()
    plan = agent.plan(
        missing_skills=["PostgreSQL", "Docker"],
        current_skills=["Python", "FastAPI"],
        session=db_session,
    )

    assert isinstance(plan, list)
    assert len(plan) == 2
    skills = {item["skill"] for item in plan}
    assert {"PostgreSQL", "Docker"}.issubset(skills)
    for item in plan:
        assert item["difficulty"] in ("入门", "进阶", "高级")
        assert item["estimated_weeks"] > 0
        assert isinstance(item["prerequisites"], list)


def test_skill_advisor(db_session):
    job = _make_job(
        db_session,
        title="Python 后端工程师",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    agent = SkillAdvisor()
    profile = {"skills": ["Python", "FastAPI"]}
    match_result = {
        "match_score": 0.66,
        "matched_skills": ["Python", "FastAPI"],
        "missing_skills": ["PostgreSQL"],
        "transferable_skills": [],
    }
    advice = agent.advise(profile, job, match_result)

    assert isinstance(advice, str)
    assert len(advice) > 0
    assert "匹配度" in advice


def test_langgraph_workflow_compiles_and_runs(db_session):
    job = _make_job(
        db_session,
        title="Python 后端工程师",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    graph = build_job_match_graph(db_session)
    assert graph is not None

    state = {
        "input_text": job.description,
        "profile": {"skills": ["Python", "FastAPI"]},
        "target_job": job,
        "job_data": [
            {
                "title": job.title,
                "city": job.city,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            }
        ],
    }
    config = {"configurable": {"session": db_session}}
    final_state = graph.invoke(state, config=config)

    assert final_state["parsed_jd"] is not None
    assert final_state["match_result"] is not None
    assert final_state["trend_analysis"] is not None
    assert isinstance(final_state["learning_path"], list)
    assert final_state["advice"]
