import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.agents.governance import GovernanceAgent
from app.agents.matcher import CaseMatcherAgent
from app.agents.predictor import RiskPredictorAgent
from app.agents.scanner import SentimentScannerAgent
from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, db: Session, prompt_variants: dict[str, str] | None = None):
        self.db = db
        self.retriever = HybridRetriever(db)
        self.prompt_variants = prompt_variants or {}
        self.scanner = SentimentScannerAgent(prompt_variant=self.prompt_variants.get("scanner"))
        self.matcher = CaseMatcherAgent(prompt_variant=self.prompt_variants.get("matcher"))
        self.predictor = RiskPredictorAgent(prompt_variant=self.prompt_variants.get("predictor"))
        self.governance = GovernanceAgent(prompt_variant=self.prompt_variants.get("governance"))

    def process(self, text: str, enterprise_hint: str | None = None) -> dict[str, Any]:
        start_time = time.time()
        logger.info(f"Processing sentiment: {text[:80]}...")

        # Step 1: Scanner
        scan_result = self.scanner.run({"text": text})
        reasoning_chain = [
            {"step": "scan", "agent": "scanner", "output": scan_result}
        ]

        # Step 2: Retrieve context (cases + enterprise)
        industry = scan_result.get("industry", "")
        risk_type = scan_result.get("risk_type", "")
        entities = scan_result.get("entities", [])

        candidate_cases = self.retriever.retrieve_cases(
            query=text,
            industry=industry if industry else None,
            risk_type=risk_type if risk_type else None,
            top_k=5,
        )
        enterprise = self._match_enterprise(enterprise_hint, entities)

        # Step 3: Matcher
        matcher_result = self.matcher.run(
            {
                "sentiment_text": text,
                "candidate_cases": candidate_cases,
            }
        )
        reasoning_chain.append({"step": "match", "agent": "matcher", "output": matcher_result})

        matched_ids = matcher_result.get("matched_case_ids", [])
        matched_cases = (
            self.db.query(RiskCase).filter(RiskCase.id.in_(matched_ids)).all()
            if matched_ids
            else []
        )
        case_summary = "\n".join(
            f"{c.title}（{c.risk_type}，{c.risk_level}）: {c.summary}" for c in matched_cases
        ) or "无匹配案例"

        enterprise_profile = self._format_enterprise(enterprise)

        # Step 4: Predictor
        predictor_result = self.predictor.run(
            {
                "sentiment_text": text,
                "case_summary": case_summary,
                "enterprise_profile": enterprise_profile,
            }
        )
        reasoning_chain.append(
            {"step": "predict", "agent": "predictor", "output": predictor_result}
        )

        risk_level = predictor_result.get("risk_level", "中")

        # Step 5: Governance
        playbook = "\n".join(
            f"{c.title}: {c.governance_playbook.get('summary', '无')}"
            for c in matched_cases
            if c.governance_playbook
        )
        governance_result = self.governance.run(
            {
                "sentiment_text": text,
                "risk_level": risk_level,
                "playbook": playbook,
            }
        )
        reasoning_chain.append(
            {"step": "govern", "agent": "governance", "output": governance_result}
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "text": text,
            "scan": scan_result,
            "matched_cases": [
                {"id": c.id, "title": c.title, "risk_level": c.risk_level, "risk_type": c.risk_type}
                for c in matched_cases
            ],
            "enterprise": (
                {"id": enterprise.id, "name": enterprise.name, "industry": enterprise.industry}
                if enterprise
                else None
            ),
            "prediction": predictor_result,
            "governance": governance_result,
            "reasoning_chain": reasoning_chain,
            "response_time_ms": elapsed_ms,
            "prompt_variants": self.prompt_variants,
        }

    def _match_enterprise(self, hint: str | None, entities: list[str]) -> Enterprise | None:
        if hint:
            return self.db.query(Enterprise).filter(Enterprise.name.contains(hint)).first()
        for entity in entities:
            ent = self.db.query(Enterprise).filter(Enterprise.name.contains(entity)).first()
            if ent:
                return ent
        return None

    def _format_enterprise(self, enterprise: Enterprise | None) -> str:
        if not enterprise:
            return "无企业画像"
        tags = ", ".join(enterprise.business_tags or [])
        return (
            f"企业：{enterprise.name}，行业：{enterprise.industry}，"
            f"规模：{enterprise.scale}，地区：{enterprise.region}，"
            f"业务标签：{tags}，风险画像：{enterprise.risk_profile}"
        )
