import logging
from typing import Any

from sqlalchemy.orm import Session

from app.data.generator import generate_cases, generate_enterprises, generate_sentiment_events
from app.models.case import RiskCase
from app.models.enterprise import Enterprise
from app.models.sentiment import SentimentEvent
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
        # Still seed events if none exist
        _seed_events_if_empty(db, n_enterprises, n_cases)
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

    # Seed sentiment events
    _seed_events(db, enterprises, cases)

    return {
        "enterprises": len(ent_records),
        "cases": len(case_records),
        "indexed": len(case_records),
    }


def _seed_events_if_empty(db: Session, n_enterprises: int, n_cases: int):
    """When enterprises/cases already exist but events don't, seed events only."""
    existing_events = db.query(SentimentEvent).count()
    if existing_events > 0:
        return
    # Load existing enterprises/cases for association
    ents = [{"name": e.name, "industry": e.industry} for e in db.query(Enterprise).all()]
    cases = [{"id": c.id} for c in db.query(RiskCase).all()]
    _seed_events(db, ents, cases)


def init_real_data(db: Session) -> dict[str, Any]:
    """使用爬虫采集真实数据填充数据库，替代 Faker 假数据。

    调用 DataInitializer 执行：爬虫采集 → 清洗管线
    → 入库（RiskCase / Enterprise / SentimentEvent）。
    """
    from app.data.init_real_data import DataInitializer

    initializer = DataInitializer(db)
    return initializer.run()


def _seed_events(db: Session, enterprises: list, cases: list):
    existing_events = db.query(SentimentEvent).count()
    if existing_events > 0:
        logger.info("Sentiment events already exist (%s); skipping", existing_events)
        return

    events = generate_sentiment_events(n=80, enterprises=enterprises, cases=cases)
    for ev in events:
        record = SentimentEvent(**ev)
        db.add(record)
    db.commit()
    logger.info("Seeded %s sentiment events", len(events))
