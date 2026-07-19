import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.agents.orchestrator import AgentOrchestrator
from app.agents.prompts import PROMPT_VARIANTS, get_template
from app.config import get_settings
from app.models.evaluation import EvaluationRun, PromptVariant
from app.models.sentiment import SentimentEvent

logger = logging.getLogger(__name__)

LEVEL_TO_INT = {"低": 1, "中": 2, "高": 3, "极高": 4}
_settings = get_settings()


def _level_to_int(level: str | None) -> int:
    return LEVEL_TO_INT.get(level or "", 0)


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_prompt_variants(self):
        """Seed prompt variants if not present."""
        existing = {pv.name for pv in self.db.query(PromptVariant).all()}
        for variant in PROMPT_VARIANTS:
            if variant["name"] not in existing:
                self.db.add(
                    PromptVariant(
                        name=variant["name"],
                        agent_type=variant["agent_type"],
                        technique=variant["technique"],
                        template=get_template(variant["name"]),
                        is_baseline=variant["is_baseline"],
                        variant_metadata={},
                    )
                )
        self.db.commit()

    def run_ab_test(
        self,
        dataset: list[dict[str, Any]],
        agent_type: str | None = None,
    ) -> dict[str, Any]:
        """Run A/B test across prompt variants.

        dataset: list of {"text": str, "true_risk_level": str, "true_risk_type": str}
        """
        self.ensure_prompt_variants()
        variants = self.db.query(PromptVariant)
        if agent_type:
            variants = variants.filter(PromptVariant.agent_type == agent_type)
        variants = variants.all()

        results: dict[str, dict[str, Any]] = {}
        for variant in variants:
            results[variant.name] = {
                "technique": variant.technique,
                "agent_type": variant.agent_type,
                "correct_level": 0,
                "correct_type": 0,
                "total": 0,
                "response_times": [],
                "details": [],
            }

        for item in dataset:
            text = item["text"]
            true_level = item.get("true_risk_level", "")
            true_type = item.get("true_risk_type", "")

            for variant in variants:
                pv = {variant.agent_type: variant.name}
                try:
                    start = time.time()
                    if _settings.use_langgraph:
                        from app.agents.workflow import run_analysis
                        out = run_analysis(self.db, text, prompt_variants=pv)
                    else:
                        orchestrator = AgentOrchestrator(self.db, prompt_variants=pv)
                        out = orchestrator.process(text)
                    elapsed = int((time.time() - start) * 1000)

                    pred_level = out["prediction"].get("risk_level", "")
                    pred_type = out["prediction"].get("risk_type", "")

                    level_ok = pred_level == true_level
                    type_ok = pred_type == true_type
                    # Treat "relevant" as true if either level or type matches
                    relevant_ok = level_ok or type_ok

                    results[variant.name]["correct_level"] += int(level_ok)
                    results[variant.name]["correct_type"] += int(type_ok)
                    results[variant.name]["total"] += 1
                    results[variant.name]["response_times"].append(elapsed)
                    results[variant.name]["details"].append(
                        {
                            "text": text[:80],
                            "true_level": true_level,
                            "pred_level": pred_level,
                            "true_type": true_type,
                            "pred_type": pred_type,
                            "relevant_ok": relevant_ok,
                            "latency_ms": elapsed,
                        }
                    )
                except Exception as e:
                    logger.error(f"A/B test error for {variant.name}: {e}")
                    results[variant.name]["total"] += 1

        # Compute metrics
        summary = {}
        for name, r in results.items():
            total = max(r["total"], 1)
            avg_latency = sum(r["response_times"]) / max(len(r["response_times"]), 1)
            summary[name] = {
                "technique": r["technique"],
                "agent_type": r["agent_type"],
                "accuracy_level": round(r["correct_level"] / total, 3),
                "accuracy_type": round(r["correct_type"] / total, 3),
                "recall_relevant": round(r["correct_level"] / total, 3),
                "avg_latency_ms": round(avg_latency, 1),
                "samples": total,
            }

        run = EvaluationRun(
            name=f"A/B {agent_type or 'all'} agents",
            dataset_size=len(dataset),
            metrics={"summary": summary},
            variant_results=results,
        )
        self.db.add(run)
        self.db.commit()

        return {
            "run_id": run.id,
            "dataset_size": len(dataset),
            "summary": summary,
        }

    def compute_overall_metrics(self) -> dict[str, Any]:
        events = self.db.query(SentimentEvent).filter(SentimentEvent.status == "processed").all()
        total = len(events)
        if total == 0:
            return {"total": 0, "accuracy": 0, "recall": 0, "avg_response_time_ms": 0}

        labeled = [e for e in events if e.labeled_risk_level is not None]
        correct = sum(1 for e in labeled if e.is_correct == 1)
        accuracy = correct / max(len(labeled), 1)
        avg_latency = sum(e.response_time_ms or 0 for e in events) / total
        return {
            "total": total,
            "labeled": len(labeled),
            "accuracy": round(accuracy, 3),
            "recall": round(accuracy, 3),
            "avg_response_time_ms": round(avg_latency, 1),
        }
