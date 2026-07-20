from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _load_json_list(value: Any) -> list[Any]:
    """将 ORM 中存储的 JSON 字符串解析为列表。"""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


# ---------------------------------------------------------------------------
# 通用响应包装
# ---------------------------------------------------------------------------
class ApiResponse(BaseModel):
    """统一 API 响应结构。"""

    code: int = 0
    data: Any | None = None
    message: str = "ok"


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------
class SkillOut(BaseModel):
    id: int
    name: str
    category: str
    aliases: list[str]
    definition: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("aliases", mode="before")
    @classmethod
    def _parse_aliases(cls, v: Any) -> list[str]:
        return [str(x) for x in _load_json_list(v)]


class SkillListOut(BaseModel):
    total: int
    items: list[SkillOut]


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class CompanyOut(BaseModel):
    id: int
    name: str
    industry: str
    size: str
    city: str

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
class JobOut(BaseModel):
    id: int
    title: str
    company: CompanyOut
    city: str
    salary_min: int
    salary_max: int
    experience_level: str
    education_level: str
    required_skills: list[str]
    description: str
    posted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("required_skills", mode="before")
    @classmethod
    def _parse_required_skills(cls, v: Any) -> list[str]:
        return [str(x) for x in _load_json_list(v)]


class JobListParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    q: str | None = None
    city: str | None = None
    industry: str | None = None
    experience_level: str | None = None


class JobListOut(BaseModel):
    total: int
    page: int
    size: int
    items: list[JobOut]


class JobSearchQuery(BaseModel):
    query: str
    top_k: int = Field(10, ge=1, le=50)
    city: str | None = None
    industry: str | None = None
    experience_level: str | None = None


class JobSearchResult(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    source: str = "chroma"


class JobStatisticsOut(BaseModel):
    total_jobs: int
    total_companies: int
    avg_salary_min: int
    avg_salary_max: int
    top_cities: list[dict[str, Any]]
    top_industries: list[dict[str, Any]]
    hot_skills: list[dict[str, Any]]
    experience_distribution: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# UserSkillProfile
# ---------------------------------------------------------------------------
class UserSkillProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    skills: list[str]
    experience_level: str = "不限"
    target_job_titles: list[str] = []


class UserSkillProfileOut(BaseModel):
    id: int
    name: str
    skills: list[str]
    experience_level: str
    target_job_titles: list[str]
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("skills", "target_job_titles", mode="before")
    @classmethod
    def _parse_profile_lists(cls, v: Any) -> list[str]:
        return [str(x) for x in _load_json_list(v)]


class UserSkillProfileListOut(BaseModel):
    total: int
    items: list[UserSkillProfileOut]


# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------
class MatchResultOut(BaseModel):
    id: int
    user_profile_id: int
    job_id: int
    match_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    transferable_skills: list[str]
    analysis_summary: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("matched_skills", "missing_skills", "transferable_skills", mode="before")
    @classmethod
    def _parse_match_lists(cls, v: Any) -> list[str]:
        return [str(x) for x in _load_json_list(v)]


class MatchRequest(BaseModel):
    profile_id: int
    job_id: int


class MatchResultListOut(BaseModel):
    total: int
    items: list[MatchResultOut]


# ---------------------------------------------------------------------------
# JD Parse
# ---------------------------------------------------------------------------
class JDParseRequest(BaseModel):
    jd_text: str = Field(..., min_length=10)


class JDParseOut(BaseModel):
    title: str
    company: str
    required_skills: list[str]
    experience_level: str
    education_level: str
    implicit_needs: list[str]


# ---------------------------------------------------------------------------
# LearningPath
# ---------------------------------------------------------------------------
class LearningPathItem(BaseModel):
    skill: str
    difficulty: str
    estimated_weeks: int
    resource_type: str
    prerequisites: list[str]


class LearningPathRequest(BaseModel):
    profile_id: int
    job_id: int


class LearningPathOut(BaseModel):
    profile_id: int
    job_id: int
    learning_path: list[LearningPathItem]


# ---------------------------------------------------------------------------
# Trend
# ---------------------------------------------------------------------------
class TrendAnalysisOut(BaseModel):
    summary: str
    top_skills: list[str]
    avg_salary_range: str
    hot_job_titles: list[str]
    key_metrics: dict[str, Any]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardOut(BaseModel):
    jobs: JobStatisticsOut
    trends: TrendAnalysisOut


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------
class MatchStreamRequest(BaseModel):
    jd_text: str | None = None
    profile_id: int | None = None
    profile: dict[str, Any] | None = None
    job_id: int | None = None
    job_data: list[dict[str, Any]] | None = None
