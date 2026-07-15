from typing import Any

from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.models.sentiment import SentimentEvent


class SentimentService:
    def __init__(self, db: Session):
        self.db = db

    def analyze(
        self,
        text: str,
        source: str = "manual",
        enterprise_hint: str | None = None,
        prompt_variants: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        orchestrator = AgentOrchestrator(self.db, prompt_variants=prompt_variants)
        result = orchestrator.process(text, enterprise_hint=enterprise_hint)

        # Persist event
        event = SentimentEvent(
            title=text[:120],
            content=text,
            source=source,
            enterprise_name=(
                result.get("enterprise", {}).get("name") if result.get("enterprise") else None
            ),
            risk_level=result["prediction"].get("risk_level"),
            risk_type=result["prediction"].get("risk_type"),
            risk_score=result["prediction"].get("risk_score", 0.0),
            matched_case_ids=[c["id"] for c in result["matched_cases"]],
            governance_plan=result["governance"],
            reasoning_chain=result["reasoning_chain"],
            response_time_ms=result["response_time_ms"],
            prompt_variant=result["prompt_variants"].get("scanner"),
            status="processed",
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        result["event_id"] = event.id
        return result

    def list_events(self, skip: int = 0, limit: int = 20) -> list[SentimentEvent]:
        return (
            self.db.query(SentimentEvent)
            .order_by(SentimentEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
