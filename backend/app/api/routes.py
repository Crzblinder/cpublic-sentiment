"""新版岗位技能图谱与人才匹配 API 路由。"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.graph_state import JobMatchState
from app.agents.trend_predictor import TrendPredictor
from app.agents.workflow import run_job_match_stream
from app.api.schemas import (
    ApiResponse,
    JDParseOut,
    JDParseRequest,
    JobListOut,
    JobListParams,
    JobOut,
    JobSearchResult,
    LearningPathOut,
    LearningPathRequest,
    MatchRequest,
    MatchResultListOut,
    MatchResultOut,
    MatchStreamRequest,
    SkillListOut,
    SkillOut,
    UserSkillProfileCreate,
    UserSkillProfileListOut,
    UserSkillProfileOut,
)
from app.models import Job, UserSkillProfile
from app.models.base import get_db
from app.services.jd_service import JDService
from app.services.job_service import JobService
from app.services.matching_service import MatchingService
from app.services.skill_service import SkillService

logger = logging.getLogger(__name__)

api_router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _success(data: Any, message: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, data=data, message=message)


def _job_to_dict(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "title": job.title,
        "company": {
            "id": job.company.id,
            "name": job.company.name,
            "industry": job.company.industry,
            "size": job.company.size,
            "city": job.company.city,
        },
        "city": job.city,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "experience_level": job.experience_level,
        "education_level": job.education_level,
        "required_skills": _load_json_list(job.required_skills),
        "description": job.description,
        "posted_at": job.posted_at,
    }


def _profile_to_dict(profile: UserSkillProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "name": profile.name,
        "skills": _load_json_list(profile.skills),
        "experience_level": profile.experience_level,
        "target_job_titles": _load_json_list(profile.target_job_titles),
        "created_at": profile.created_at,
    }


def _load_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@api_router.get("/jobs/health")
def jobs_health() -> ApiResponse:
    return _success({"status": "ok"}, message="服务健康")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
@api_router.get("/jobs", response_model=ApiResponse)
def list_jobs(
    params: JobListParams = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = JobService(db)
    result = service.list_jobs(
        page=params.page,
        size=params.size,
        q=params.q,
        city=params.city,
        industry=params.industry,
        experience_level=params.experience_level,
    )
    result["items"] = [JobOut.model_validate(_job_to_dict(job)) for job in result["items"]]
    return _success(JobListOut.model_validate(result).model_dump())


@api_router.get("/jobs/{job_id}", response_model=ApiResponse)
def get_job(job_id: int, db: Session = Depends(get_db)) -> ApiResponse:
    service = JobService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"岗位不存在: {job_id}")
    return _success(JobOut.model_validate(_job_to_dict(job)).model_dump())


@api_router.get("/jobs/search", response_model=ApiResponse)
def search_jobs(
    query: str = Query(..., min_length=1),
    top_k: int = Query(10, ge=1, le=50),
    city: str | None = None,
    industry: str | None = None,
    experience_level: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = JobService(db)
    results = service.search_jobs(
        query=query,
        top_k=top_k,
        city=city,
        industry=industry,
        experience_level=experience_level,
    )
    return _success([JobSearchResult.model_validate(r).model_dump() for r in results])


@api_router.post("/jobs/parse", response_model=ApiResponse)
def parse_jd(payload: JDParseRequest, db: Session = Depends(get_db)) -> ApiResponse:
    service = JDService()
    try:
        parsed = service.parse_jd_text(payload.jd_text)
    except Exception as exc:
        logger.exception("JD 解析失败")
        raise HTTPException(status_code=500, detail=f"JD 解析失败: {exc}") from exc
    return _success(JDParseOut.model_validate(parsed).model_dump())


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
@api_router.get("/skills", response_model=ApiResponse)
def list_skills(
    category: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = SkillService(db)
    result = service.list_skills(category=category)
    return _success(SkillListOut.model_validate(result).model_dump())


@api_router.get("/skills/{skill_id}", response_model=ApiResponse)
def get_skill(skill_id: int, db: Session = Depends(get_db)) -> ApiResponse:
    service = SkillService(db)
    skill = service.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"技能不存在: {skill_id}")
    return _success(SkillOut.model_validate(skill).model_dump())


@api_router.get("/skills/{skill_id}/related", response_model=ApiResponse)
def get_related_skills(
    skill_id: int,
    relation_type: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = SkillService(db)
    skill = service.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"技能不存在: {skill_id}")
    related = service.get_related_skills(
        skill_name=skill.name,
        relation_type=relation_type,
    )
    return _success(related)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------
@api_router.post("/profiles", response_model=ApiResponse)
def create_profile(
    payload: UserSkillProfileCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    import json as _json

    profile = UserSkillProfile(
        name=payload.name,
        skills=_json.dumps(payload.skills, ensure_ascii=False),
        experience_level=payload.experience_level,
        target_job_titles=_json.dumps(payload.target_job_titles, ensure_ascii=False),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _success(UserSkillProfileOut.model_validate(profile).model_dump())


@api_router.get("/profiles", response_model=ApiResponse)
def list_profiles(db: Session = Depends(get_db)) -> ApiResponse:
    items = db.query(UserSkillProfile).order_by(UserSkillProfile.created_at.desc()).all()
    return _success(
        UserSkillProfileListOut(
            total=len(items),
            items=[UserSkillProfileOut.model_validate(p) for p in items],
        ).model_dump()
    )


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------
@api_router.post("/matches", response_model=ApiResponse)
def create_match(
    payload: MatchRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = MatchingService(db)
    try:
        match_result = service.match_profile_to_job(
            profile_id=payload.profile_id,
            job_id=payload.job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("匹配失败")
        raise HTTPException(status_code=500, detail=f"匹配失败: {exc}") from exc
    return _success(MatchResultOut.model_validate(match_result).model_dump())


@api_router.get("/matches/{match_id}", response_model=ApiResponse)
def get_match(match_id: int, db: Session = Depends(get_db)) -> ApiResponse:
    service = MatchingService(db)
    match_result = service.get_match_result(match_id)
    if match_result is None:
        raise HTTPException(status_code=404, detail=f"匹配结果不存在: {match_id}")
    return _success(MatchResultOut.model_validate(match_result).model_dump())


@api_router.get("/matches", response_model=ApiResponse)
def list_matches(
    profile_id: int | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = MatchingService(db)
    result = service.list_match_results(profile_id=profile_id)
    return _success(
        MatchResultListOut(
            total=result["total"],
            items=[MatchResultOut.model_validate(m) for m in result["items"]],
        ).model_dump()
    )


@api_router.post("/matches/learning-path", response_model=ApiResponse)
def generate_learning_path(
    payload: LearningPathRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    service = MatchingService(db)
    try:
        result = service.generate_learning_path(
            profile_id=payload.profile_id,
            job_id=payload.job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("生成学习路径失败")
        raise HTTPException(status_code=500, detail=f"生成学习路径失败: {exc}") from exc
    return _success(LearningPathOut.model_validate(result).model_dump())


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------
@api_router.get("/trends", response_model=ApiResponse)
def get_trends(db: Session = Depends(get_db)) -> ApiResponse:
    job_data = []
    for job in db.query(Job).all():
        job_data.append(
            {
                "title": job.title,
                "city": job.city,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "required_skills": _load_json_list(job.required_skills),
            }
        )

    agent = TrendPredictor()
    trend = agent.predict(job_data)
    return _success(
        {
            "summary": trend.get("summary", ""),
            "top_skills": trend.get("top_skills", []),
            "avg_salary_range": trend.get("avg_salary_range", ""),
            "hot_job_titles": trend.get("hot_job_titles", []),
            "key_metrics": trend.get("key_metrics", {}),
        }
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@api_router.get("/dashboard", response_model=ApiResponse)
def get_dashboard(db: Session = Depends(get_db)) -> ApiResponse:
    job_service = JobService(db)
    skill_service = SkillService(db)

    job_stats = job_service.get_job_statistics()
    skill_stats = skill_service.get_skill_statistics()

    job_data = []
    for job in db.query(Job).all():
        job_data.append(
            {
                "title": job.title,
                "city": job.city,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "required_skills": _load_json_list(job.required_skills),
            }
        )
    agent = TrendPredictor()
    trend = agent.predict(job_data)

    return _success(
        {
            "jobs": job_stats,
            "skills": skill_stats,
            "trends": {
                "summary": trend.get("summary", ""),
                "top_skills": trend.get("top_skills", []),
                "avg_salary_range": trend.get("avg_salary_range", ""),
                "hot_job_titles": trend.get("hot_job_titles", []),
                "key_metrics": trend.get("key_metrics", {}),
            },
        }
    )


# ---------------------------------------------------------------------------
# SSE Stream
# ---------------------------------------------------------------------------
async def _match_stream_events(
    db: Session,
    payload: MatchStreamRequest,
) -> Any:
    input_text = payload.jd_text or ""
    target_job = None
    profile = payload.profile or {}

    if payload.job_id is not None:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if job is not None:
            target_job = job
            input_text = input_text or job.description

    if payload.profile_id is not None:
        profile_obj = (
            db.query(UserSkillProfile)
            .filter(UserSkillProfile.id == payload.profile_id)
            .first()
        )
        if profile_obj is not None:
            profile = _profile_to_dict(profile_obj)

    job_data = payload.job_data or []
    if not job_data:
        for job in db.query(Job).all():
            job_data.append(
                {
                    "title": job.title,
                    "city": job.city,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "required_skills": _load_json_list(job.required_skills),
                }
            )

    state: JobMatchState = {
        "input_text": input_text,
        "profile": profile,
        "target_job": target_job,
        "job_data": job_data,
    }

    try:
        async for event in run_job_match_stream(db, state):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except Exception as exc:
        logger.exception("流式分析失败")
        error_event = {
            "node": "error",
            "status": "failed",
            "message": str(exc),
        }
        yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"


@api_router.post("/matches/stream")
def match_stream(
    payload: MatchStreamRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        _match_stream_events(db, payload),
        media_type="text/event-stream",
    )
