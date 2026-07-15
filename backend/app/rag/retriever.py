import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.rag.embeddings import get_embedding_model
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retrieval combining vector similarity with structured SQL filters."""

    def __init__(self, db: Session):
        self.db = db
        self.case_store = VectorStore("risk_cases")
        self.enterprise_store = VectorStore("enterprises")
        self.embedder = get_embedding_model()

    def retrieve_cases(
        self,
        query: str,
        industry: str | None = None,
        risk_type: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        start = time.time()

        # SQL pre-filter to narrow candidate set (keeps vector search fast)
        q = self.db.query(RiskCase)
        if industry:
            q = q.filter(RiskCase.industry == industry)
        if risk_type:
            q = q.filter(RiskCase.risk_type == risk_type)
        sql_candidates = q.limit(200).all()

        candidate_ids = [str(c.id) for c in sql_candidates]

        # If vector store already has embeddings, do vector rerank
        if candidate_ids:
            try:
                where = {"id": {"$in": candidate_ids}}
                if industry:
                    where["industry"] = industry
                if risk_type:
                    where["risk_type"] = risk_type
                results = self.case_store.query([query], n_results=min(top_k * 2, 20), where=where)
                ids = results["ids"][0]
                distances = results["distances"][0]
                case_map = {str(c.id): c for c in sql_candidates}
                output = []
                for cid, dist in zip(ids, distances):
                    c = case_map.get(cid)
                    if c:
                        output.append(
                            {
                                "id": c.id,
                                "title": c.title,
                                "summary": c.summary,
                                "industry": c.industry,
                                "risk_type": c.risk_type,
                                "risk_level": c.risk_level,
                                "vector_score": float(1 - dist),
                            }
                        )
                elapsed = int((time.time() - start) * 1000)
                logger.debug(f"Hybrid case retrieval took {elapsed}ms")
                return output[:top_k]
            except Exception as e:
                logger.warning(f"Vector retrieval failed: {e}; falling back to SQL")

        # Fallback: keyword-ish SQL ordering by title relevance
        if industry and risk_type:
            q = q.order_by(RiskCase.risk_level.desc())
        fallback = [
            {
                "id": c.id,
                "title": c.title,
                "summary": c.summary,
                "industry": c.industry,
                "risk_type": c.risk_type,
                "risk_level": c.risk_level,
                "vector_score": None,
            }
            for c in sql_candidates[:top_k]
        ]
        return fallback

    def retrieve_enterprises(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        try:
            results = self.enterprise_store.query([query], n_results=top_k)
            ids = results["ids"][0]
            enterprises = (
                self.db.query(Enterprise).filter(Enterprise.id.in_([int(i) for i in ids])).all()
            )
            ent_map = {str(e.id): e for e in enterprises}
            return [
                {
                    "id": ent_map[i].id,
                    "name": ent_map[i].name,
                    "industry": ent_map[i].industry,
                }
                for i in ids
                if i in ent_map
            ]
        except Exception as e:
            logger.warning(f"Enterprise retrieval failed: {e}")
            return []

    def index_case(self, case: RiskCase):
        doc = (
            f"{case.title}。{case.summary}。"
            f"行业：{case.industry}，风险类型：{case.risk_type}，等级：{case.risk_level}。"
        )
        self.case_store.upsert(
            ids=[str(case.id)],
            documents=[doc],
            metadatas=[
                {
                    "id": str(case.id),
                    "industry": case.industry,
                    "risk_type": case.risk_type,
                }
            ],
        )

    def index_enterprise(self, enterprise: Enterprise):
        tags = "，".join(enterprise.business_tags or [])
        doc = (
            f"{enterprise.name}。行业：{enterprise.industry}，"
            f"规模：{enterprise.scale}，地区：{enterprise.region}，业务标签：{tags}。"
        )
        self.enterprise_store.upsert(
            ids=[str(enterprise.id)],
            documents=[doc],
            metadatas=[{"id": str(enterprise.id), "industry": enterprise.industry}],
        )
