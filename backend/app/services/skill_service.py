"""技能相关服务。"""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.graph.skill_graph import build_graph_from_db, get_related_skills
from app.models import Job, Skill, SkillRelation

logger = logging.getLogger(__name__)


def _parse_skills(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


class SkillService:
    def __init__(self, db: Session):
        self.db = db

    def list_skills(self, category: str | None = None) -> dict[str, Any]:
        query = self.db.query(Skill)
        if category:
            query = query.filter(Skill.category == category)
        items = query.order_by(Skill.name).all()
        return {"total": len(items), "items": items}

    def get_skill(self, skill_id: int) -> Skill | None:
        return self.db.query(Skill).filter(Skill.id == skill_id).first()

    def get_related_skills(
        self,
        skill_name: str,
        relation_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        try:
            graph = build_graph_from_db(self.db)
        except Exception as exc:
            logger.warning("Failed to build skill graph: %s", exc)
            return []
        return get_related_skills(
            graph, skill_name, relation_type=relation_type, limit=limit
        )

    def get_skill_statistics(self) -> dict[str, Any]:
        total_skills = self.db.query(Skill).count()
        total_relations = self.db.query(SkillRelation).count()

        category_distribution = (
            self.db.query(Skill.category, func.count(Skill.id).label("count"))
            .group_by(Skill.category)
            .order_by(func.count(Skill.id).desc())
            .all()
        )

        # 技能热度：按在岗位需求中出现次数统计
        skill_counter: Counter = Counter()
        for row in self.db.query(Job.required_skills).all():
            for skill in _parse_skills(row[0]):
                skill_counter[skill] += 1

        hot_skills = [
            {"skill": skill, "count": count}
            for skill, count in skill_counter.most_common(20)
        ]

        relation_type_distribution = (
            self.db.query(
                SkillRelation.relation_type, func.count(SkillRelation.id).label("count")
            )
            .group_by(SkillRelation.relation_type)
            .order_by(func.count(SkillRelation.id).desc())
            .all()
        )

        return {
            "total_skills": total_skills,
            "total_relations": total_relations,
            "category_distribution": [
                {"category": c, "count": n} for c, n in category_distribution
            ],
            "hot_skills": hot_skills,
            "relation_type_distribution": [
                {"relation_type": r, "count": n} for r, n in relation_type_distribution
            ],
        }
