import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.graph.skill_graph import build_graph_from_db, get_related_skills
from app.models import Job

logger = logging.getLogger(__name__)


def _load_skills(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


class TalentMatcher(BaseAgent):
    """人才匹配 Agent。

    将用户技能画像与目标岗位进行匹配，计算匹配分数、缺失技能与可迁移技能。
    """

    name = "talent_matcher"

    def match(
        self,
        profile_skills: list[str],
        job: Job,
        session: Session,
    ) -> dict[str, Any]:
        """计算人才与岗位的匹配结果。"""
        system_prompt = self._load_prompt()
        job_skills = _load_skills(job.required_skills)
        user_prompt = (
            f"用户技能：{', '.join(profile_skills)}\n"
            f"目标岗位：{job.title}\n"
            f"岗位要求技能：{', '.join(job_skills)}\n"
            f"请返回匹配结果 JSON。"
        )

        result = self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        if result.get("simulated"):
            return self._rule_based_match(profile_skills, job, session)

        return self._normalize_match_result(result, profile_skills, job_skills, session)

    def _rule_based_match(
        self,
        profile_skills: list[str],
        job: Job,
        session: Session,
    ) -> dict[str, Any]:
        """无 LLM 时的规则匹配。"""
        job_skills = _load_skills(job.required_skills)
        profile_set = set(profile_skills)
        required_set = set(job_skills)

        matched = list(profile_set & required_set)
        missing = list(required_set - profile_set)

        # 可迁移技能：通过 skill_graph 的 similarity 关系查找
        transferable = self._find_transferable_skills(
            profile_set, required_set, missing, session
        )

        score = self._compute_score(matched, missing, required_set)

        return {
            "match_score": round(score, 3),
            "matched_skills": matched,
            "missing_skills": missing,
            "transferable_skills": transferable,
            "analysis_summary": (
                f"匹配度 {score:.1%}，掌握 {len(matched)} 项核心技能，"
                f"缺失 {len(missing)} 项，可迁移 {len(transferable)} 项。"
            ),
        }

    def _normalize_match_result(
        self,
        result: dict[str, Any],
        profile_skills: list[str],
        job_skills: list[str],
        session: Session,
    ) -> dict[str, Any]:
        """校验并补充 LLM 返回的匹配结果。"""
        profile_set = set(profile_skills)
        required_set = set(job_skills)

        matched = result.get("matched_skills") or []
        missing = result.get("missing_skills") or []
        transferable = result.get("transferable_skills") or []

        matched = [str(x) for x in matched if x in required_set and x in profile_set]
        missing = [str(x) for x in missing if x in required_set and x not in profile_set]
        transferable = [str(x) for x in transferable]

        # 补充规则计算中遗漏的可迁移技能
        existing_transferable = {t.split("->")[0] for t in transferable if "->" in t}
        extra = self._find_transferable_skills(
            profile_set, required_set, missing, session
        )
        for item in extra:
            source = item.split("->")[0] if "->" in item else item
            if source not in existing_transferable:
                transferable.append(item)

        # 重新规整缺失与匹配
        all_matched_set = set(matched) | {t.split("->")[-1] for t in transferable if "->" in t}
        missing = [s for s in required_set if s not in all_matched_set]
        matched = [s for s in required_set if s in profile_set]

        score = result.get("match_score")
        score = score if isinstance(score, (int, float)) else None
        if score is None:
            score = self._compute_score(matched, missing, required_set)
        score = max(0.0, min(1.0, float(score)))

        summary = result.get("analysis_summary") or (
            f"匹配度 {score:.1%}，掌握 {len(matched)} 项核心技能，"
            f"缺失 {len(missing)} 项，可迁移 {len(transferable)} 项。"
        )

        return {
            "match_score": round(score, 3),
            "matched_skills": matched,
            "missing_skills": missing,
            "transferable_skills": transferable,
            "analysis_summary": summary,
        }

    def _find_transferable_skills(
        self,
        profile_set: set[str],
        required_set: set[str],
        missing: list[str],
        session: Session,
    ) -> list[str]:
        """基于相似关系寻找可迁移技能。"""
        transferable: list[str] = []
        try:
            graph = build_graph_from_db(session, relation_types=["similarity"])
        except Exception as exc:
            logger.warning("Failed to build skill graph for transferable lookup: %s", exc)
            return transferable

        for miss_skill in missing:
            if miss_skill not in required_set:
                continue
            related = get_related_skills(
                graph,
                miss_skill,
                relation_type="similarity",
                min_weight=0.5,
                limit=10,
            )
            for rel in related:
                neighbor = rel["skill"]
                if neighbor in profile_set:
                    transferable.append(f"{neighbor}->{miss_skill}")
                    break
        return transferable

    def _compute_score(
        self,
        matched: list[str],
        missing: list[str],
        required_set: set[str],
    ) -> float:
        """基于覆盖率和缺失惩罚计算匹配分数。"""
        if not required_set:
            return 1.0
        coverage = len(matched) / len(required_set)
        # 缺失惩罚：每个缺失技能按 0.08 惩罚，但不超过覆盖率的 50%
        penalty = min(len(missing) * 0.08, coverage * 0.5)
        return max(0.0, coverage - penalty)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """BaseAgent 抽象方法实现。"""
        profile_skills = context.get("profile_skills") or []
        job = context.get("job")
        session = context.get("session")
        if job is None or session is None:
            raise ValueError("TalentMatcher.run requires 'job' and 'session' in context")
        return self.match(profile_skills, job, session)
