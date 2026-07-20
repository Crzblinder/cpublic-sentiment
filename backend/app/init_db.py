import logging

# 导入所有模型以注册到 Base.metadata
from app import models  # noqa: F401
from app.config import get_settings
from app.data.seed import seed_database
from app.models.base import Base, SessionLocal, engine
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def init_db(seed: bool = True, rebuild_vector_store: bool = True) -> None:
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ready.")

    if seed:
        db = SessionLocal()
        try:
            result = seed_database(db, n_skills=80, n_companies=40, n_jobs=250)
            logger.info("Seed result: %s", result)
        finally:
            db.close()

    if rebuild_vector_store:
        _rebuild_vector_store()


def _rebuild_vector_store() -> None:
    """Sync Job and Skill data from SQL database into Chroma vector store."""
    db = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload

        jobs = db.query(models.Job).options(joinedload(models.Job.company)).all()
        skills = db.query(models.Skill).all()
        if not jobs and not skills:
            logger.info("No jobs or skills found; skipping vector store rebuild.")
            return

        vector_store = get_vector_store()
        logger.info("Rebuilding vector store collection '%s'...", vector_store.collection_name)
        vector_store.clear_collection()

        indexed_jobs = vector_store.add_job_documents(jobs)
        indexed_skills = vector_store.add_skill_documents(skills)
        logger.info(
            "Vector store rebuilt: %s jobs, %s skills indexed",
            indexed_jobs,
            indexed_skills,
        )
    except Exception as exc:
        logger.error(
            "Failed to rebuild vector store (retrieval features may be unavailable). "
            "Cause: %s",
            exc,
            exc_info=True,
        )
        logger.error(
            "If the embedding model '%s' could not be downloaded, please check your "
            "network connection or set HF_ENDPOINT / HF_HUB_OFFLINE appropriately.",
            get_settings().embedding_model,
        )
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
