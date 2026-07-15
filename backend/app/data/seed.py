import logging
from typing import Any

from sqlalchemy.orm import Session

from app.data.generator import generate_cases, generate_enterprises
from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


def seed_database(db: Session, n_enterprises: int = 220, n_cases: int = 520) -> dict[str, Any]:
    logger.info("Seeding enterprises and cases...")

    # Clear existing data if desired (optional; idempotent by default)
    existing_ents = db.query(Enterprise).count()
    existing_cases = db.query(RiskCase).count()
    if existing_ents > 0 or existing_cases > 0:
        logger.info(
            "Database already has %s enterprises, %s cases; skipping seed",
            existing_ents,
            existing_cases,
        )
        return {"enterprises": existing_ents, "cases": existing_cases, "indexed": 0}

    retriever = HybridRetriever(db)

    enterprises = generate_enterprises(n_enterprises)
    ent_records = []
    for ent_data in enterprises:
        record = Enterprise(**ent_data)
        db.add(record)
        ent_records.append(record)
    db.flush()

    for record in ent_records:
        retriever.index_enterprise(record)
        record.vector_id = str(record.id)

    cases = generate_cases(n_cases)
    case_records = []
    for case_data in cases:
        record = RiskCase(**case_data)
        db.add(record)
        case_records.append(record)
    db.flush()

    for record in case_records:
        retriever.index_case(record)
        record.vector_id = str(record.id)

    db.commit()
    logger.info(f"Seeded {len(ent_records)} enterprises and {len(case_records)} cases")
    return {
        "enterprises": len(ent_records),
        "cases": len(case_records),
        "indexed": len(case_records),
    }
