"""仪表盘统计服务。

提供 Dashboard 页面所需的所有聚合数据：
- 风险等级分布、行业分布、TOP10 高风险企业
- 近 30 天每日事件趋势
- 企业详情（画像 + 关联事件 + 同行业排名）
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enterprise import Enterprise
from app.models.sentiment import SentimentEvent

logger = logging.getLogger(__name__)

LEVEL_ORDER = ["低", "中", "高", "极高"]


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_stats(self) -> dict[str, Any]:
        """仪表盘汇总统计。"""
        total = self.db.query(SentimentEvent).filter(SentimentEvent.status == "processed").count()

        # 风险等级分布
        level_q = (
            self.db.query(SentimentEvent.risk_level, func.count(SentimentEvent.id))
            .filter(SentimentEvent.status == "processed", SentimentEvent.risk_level.isnot(None))
            .group_by(SentimentEvent.risk_level)
            .all()
        )
        risk_distribution = [{"name": level or "未知", "value": count} for level, count in level_q]

        # 风险类型分布
        type_q = (
            self.db.query(SentimentEvent.risk_type, func.count(SentimentEvent.id))
            .filter(SentimentEvent.status == "processed", SentimentEvent.risk_type.isnot(None))
            .group_by(SentimentEvent.risk_type)
            .order_by(func.count(SentimentEvent.id).desc())
            .limit(10)
            .all()
        )
        risk_type_distribution = [{"name": rt or "未知", "value": count} for rt, count in type_q]

        # 行业分布（通过 enterprise_name 关联）
        industry_q = (
            self.db.query(Enterprise.industry, func.count(SentimentEvent.id))
            .join(SentimentEvent, Enterprise.id == SentimentEvent.enterprise_id)
            .filter(SentimentEvent.status == "processed")
            .group_by(Enterprise.industry)
            .all()
        )
        # 也统计无企业关联的事件
        no_ent_count = (
            self.db.query(func.count(SentimentEvent.id))
            .filter(SentimentEvent.status == "processed", SentimentEvent.enterprise_id.is_(None))
            .scalar()
        )
        industry_distribution = [{"name": ind or "未知", "value": cnt} for ind, cnt in industry_q]
        if no_ent_count:
            industry_distribution.append({"name": "未关联", "value": no_ent_count})

        # TOP10 高风险企业（按关联事件的平均风险评分排序）
        top_q = (
            self.db.query(
                Enterprise.id,
                Enterprise.name,
                Enterprise.industry,
                func.avg(SentimentEvent.risk_score).label("avg_score"),
                func.count(SentimentEvent.id).label("event_count"),
            )
            .join(SentimentEvent, Enterprise.id == SentimentEvent.enterprise_id)
            .filter(SentimentEvent.status == "processed")
            .group_by(Enterprise.id)
            .order_by(func.avg(SentimentEvent.risk_score).desc())
            .limit(10)
            .all()
        )
        top_enterprises = [
            {
                "id": e.id,
                "name": e.name,
                "industry": e.industry,
                "avg_risk_score": round(float(e.avg_score or 0), 2),
                "event_count": e.event_count,
            }
            for e in top_q
        ]

        # 高风险占比
        high_count = sum(
            d["value"] for d in risk_distribution if d["name"] in ("高", "极高")
        )
        high_risk_ratio = round(high_count / max(total, 1), 3)

        # 平均响应时间
        avg_resp = (
            self.db.query(func.avg(SentimentEvent.response_time_ms))
            .filter(
                SentimentEvent.status == "processed",
                SentimentEvent.response_time_ms.isnot(None),
            )
            .scalar()
        )

        # 平均风险评分
        avg_score = (
            self.db.query(func.avg(SentimentEvent.risk_score))
            .filter(SentimentEvent.status == "processed")
            .scalar()
        )

        # 准确率
        labeled = (
            self.db.query(SentimentEvent)
            .filter(SentimentEvent.status == "processed", SentimentEvent.is_correct.isnot(None))
            .all()
        )
        correct = sum(1 for e in labeled if e.is_correct == 1)
        accuracy = round(correct / max(len(labeled), 1), 3)

        # 今日与近 7 天新增
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        today_count = (
            self.db.query(func.count(SentimentEvent.id))
            .filter(SentimentEvent.status == "processed", SentimentEvent.created_at >= today_start)
            .scalar()
        )
        week_high_count = (
            self.db.query(func.count(SentimentEvent.id))
            .filter(
                SentimentEvent.status == "processed",
                SentimentEvent.created_at >= week_start,
                SentimentEvent.risk_level.in_(["高", "极高"]),
            )
            .scalar()
        )

        return {
            "summary": {
                "total_events": total,
                "today_events": today_count or 0,
                "week_high_risk_events": week_high_count or 0,
                "high_risk_ratio": high_risk_ratio,
                "avg_risk_score": round(float(avg_score or 0), 3),
                "avg_response_time_ms": round(float(avg_resp or 0), 1),
                "accuracy": accuracy,
                "labeled_count": len(labeled),
            },
            "risk_distribution": risk_distribution,
            "risk_type_distribution": risk_type_distribution,
            "industry_distribution": industry_distribution,
            "top_enterprises": top_enterprises,
        }

    def get_trend(self, days: int = 30) -> list[dict[str, Any]]:
        """近 N 天每日事件数量 + 平均风险评分。"""
        now = datetime.now(UTC)
        start = now - timedelta(days=days)

        rows = (
            self.db.query(
                func.date(SentimentEvent.created_at).label("date"),
                func.count(SentimentEvent.id).label("count"),
                func.avg(SentimentEvent.risk_score).label("avg_score"),
            )
            .filter(
                SentimentEvent.status == "processed",
                SentimentEvent.created_at >= start,
            )
            .group_by(func.date(SentimentEvent.created_at))
            .order_by(func.date(SentimentEvent.created_at))
            .all()
        )

        trend = []
        for r in rows:
            trend.append({
                "date": str(r.date),
                "count": r.count,
                "avg_score": round(float(r.avg_score or 0), 2),
            })
        return trend

    def get_enterprise_detail(self, enterprise_id: int) -> dict[str, Any] | None:
        """企业详情：画像 + 关联事件 + 同行业排名。"""
        ent = self.db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
        if not ent:
            return None

        # 关联事件（最近 20 条）
        events = (
            self.db.query(SentimentEvent)
            .filter(
                SentimentEvent.enterprise_id == enterprise_id,
                SentimentEvent.status == "processed",
            )
            .order_by(SentimentEvent.created_at.desc())
            .limit(20)
            .all()
        )

        # 同行业排名
        industry_peers = (
            self.db.query(
                Enterprise.id,
                Enterprise.name,
                func.avg(SentimentEvent.risk_score).label("avg_score"),
            )
            .join(SentimentEvent, Enterprise.id == SentimentEvent.enterprise_id)
            .filter(Enterprise.industry == ent.industry, SentimentEvent.status == "processed")
            .group_by(Enterprise.id)
            .order_by(func.avg(SentimentEvent.risk_score).desc())
            .limit(10)
            .all()
        )

        rank = next(
            (i + 1 for i, p in enumerate(industry_peers) if p.id == enterprise_id), None
        )

        return {
            "enterprise": {
                "id": ent.id,
                "name": ent.name,
                "industry": ent.industry,
                "scale": ent.scale,
                "region": ent.region,
                "business_tags": ent.business_tags or [],
                "risk_profile": ent.risk_profile or {},
                "risk_score_history": ent.risk_score_history or [],
            },
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "risk_level": e.risk_level,
                    "risk_type": e.risk_type,
                    "risk_score": e.risk_score,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
            "rank_in_industry": rank,
            "industry_peers": [
                {"id": p.id, "name": p.name, "avg_risk_score": round(float(p.avg_score or 0), 2)}
                for p in industry_peers
            ],
        }

    def get_enterprise_events(
        self, enterprise_id: int, skip: int = 0, limit: int = 20
    ) -> list[dict[str, Any]]:
        """企业关联的舆情事件分页列表。"""
        events = (
            self.db.query(SentimentEvent)
            .filter(
                SentimentEvent.enterprise_id == enterprise_id,
                SentimentEvent.status == "processed",
            )
            .order_by(SentimentEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "title": e.title,
                "risk_level": e.risk_level,
                "risk_type": e.risk_type,
                "risk_score": e.risk_score,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
