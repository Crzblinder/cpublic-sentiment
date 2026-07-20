"""人岗匹配与学习路径服务。"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agents.learning_planner import LearningPlanner
from app.agents.talent_matcher import TalentMatcher
from app.models import Job, MatchResult, UserSkillProfile

logger = logging.getLogger(__name__)


def _dump_list(value: list[Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_list(value: str | list[Any]) -> list[Any]:
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


class MatchingService:
    def __init__(self, db: Session):
        self.db = db

    def match_profile_to_job(self, profile_id: int, job_id: int) -> MatchResult:
        profile = (
            self.db.query(UserSkillProfile)
            .filter(UserSkillProfile.id == profile_id)
            .first()
        )
        if profile is None:
            raise ValueError(f"用户画像不存在: profile_id={profile_id}")

        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            raise ValueError(f"岗位不存在: job_id={job_id}")

        profile_skills = _load_list(profile.skills)
        matcher = TalentMatcher()
        result = matcher.match(profile_skills, job, self.db)

        match_result = MatchResult(
            user_profile_id=profile_id,
            job_id=job_id,
            match_score=float(result.get("match_score", 0.0)),
            matched_skills=_dump_list(result.get("matched_skills", [])),
            missing_skills=_dump_list(result.get("missing_skills", [])),
            transferable_skills=_dump_list(result.get("transferable_skills", [])),
            analysis_summary=result.get("analysis_summary"),
        )
        self.db.add(match_result)
        self.db.commit()
        self.db.refresh(match_result)
        return match_result

    def get_match_result(self, match_id: int) -> MatchResult | None:
        return self.db.query(MatchResult).filter(MatchResult.id == match_id).first()

    def list_match_results(
        self, profile_id: int | None = None
    ) -> dict[str, Any]:
        query = self.db.query(MatchResult)
        if profile_id is not None:
            query = query.filter(MatchResult.user_profile_id == profile_id)
        items = query.order_by(MatchResult.created_at.desc()).all()
        return {"total": len(items), "items": items}

    def generate_learning_path(
        self, profile_id: int, job_id: int
    ) -> dict[str, Any]:
        profile = (
            self.db.query(UserSkillProfile)
            .filter(UserSkillProfile.id == profile_id)
            .first()
        )
        if profile is None:
            raise ValueError(f"用户画像不存在: profile_id={profile_id}")

        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            raise ValueError(f"岗位不存在: job_id={job_id}")

        current_skills = _load_list(profile.skills)

        # 优先使用已有的最新匹配结果中的缺失技能
        latest_match = (
            self.db.query(MatchResult)
            .filter(
                MatchResult.user_profile_id == profile_id,
                MatchResult.job_id == job_id,
            )
            .order_by(MatchResult.created_at.desc())
            .first()
        )

        if latest_match:
            missing_skills = _load_list(latest_match.missing_skills)
        else:
            matcher = TalentMatcher()
            match_result = matcher.match(current_skills, job, self.db)
            missing_skills = match_result.get("missing_skills", [])

        planner = LearningPlanner()
        plan = planner.plan(missing_skills, current_skills, self.db)

        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "learning_path": plan,
        }
