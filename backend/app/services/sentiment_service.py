import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.sentiment import SentimentEvent

logger = logging.getLogger(__name__)
settings = get_settings()


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
        """分析舆情文本，自动降级处理空数据库等异常情况。"""
        try:
            if settings.use_langgraph:
                from app.agents.workflow import persist_event, run_analysis

                result = run_analysis(
                    self.db,
                    text=text,
                    enterprise_hint=enterprise_hint,
                    prompt_variants=prompt_variants,
                )
                event_id = persist_event(self.db, text, result, source=source)
                result["event_id"] = event_id
                return result
            else:
                # Fallback: 旧版 Orchestrator
                from app.agents.orchestrator import AgentOrchestrator

                orchestrator = AgentOrchestrator(self.db, prompt_variants=prompt_variants)
                result = orchestrator.process(text, enterprise_hint=enterprise_hint)

                event = SentimentEvent(
                    title=text[:120],
                    content=text,
                    source=source,
                    enterprise_name=(
                        result.get("enterprise", {}).get("name")
                        if result.get("enterprise")
                        else None
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
        except Exception as e:
            # 空数据库或其他异常时返回基础结果，避免 500 错误
            logger.warning("分析流程异常，返回基础降级结果: %s", e)
            from app.agents.scanner import SentimentScannerAgent

            scanner = SentimentScannerAgent()
            scan_result = scanner._simulate_response("", f"文本：{text}")
            risk_level = "低"
            risk_score = scan_result.get("confidence", 0.2)
            risk_type = scan_result.get("risk_type", "其他")

            # 根据置信度映射风险等级
            if risk_score >= 0.8:
                risk_level = "极高"
            elif risk_score >= 0.6:
                risk_level = "高"
            elif risk_score >= 0.4:
                risk_level = "中"

            event = SentimentEvent(
                title=text[:120],
                content=text,
                source=source,
                enterprise_name=enterprise_hint,
                risk_level=risk_level,
                risk_type=risk_type,
                risk_score=risk_score,
                governance_plan={},
                reasoning_chain=[{"agent": "fallback", "note": f"降级处理: {str(e)[:200]}"}],
                status="processed",
            )
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            return {
                "event_id": event.id,
                "text": text,
                "scan": scan_result,
                "matched_cases": [],
                "enterprise": None,
                "prediction": {
                    "risk_level": risk_level,
                    "risk_type": risk_type,
                    "risk_score": risk_score,
                },
                "governance": {},
                "reasoning_chain": event.reasoning_chain,
                "response_time_ms": 0,
                "prompt_variants": {"scanner": "fallback"},
            }

    def list_events(self, skip: int = 0, limit: int = 20) -> list[SentimentEvent]:
        return (
            self.db.query(SentimentEvent)
            .order_by(SentimentEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
