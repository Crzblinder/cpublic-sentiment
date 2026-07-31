import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import get_settings
from app.models.base import Base, engine

logger = logging.getLogger(__name__)

settings = get_settings()

# Ensure vector directory exists
os.makedirs(settings.vector_db_path, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)
    # 启动爬虫定时采集任务
    from app.crawler.scheduler import scheduler_loop
    scheduler_task = asyncio.create_task(scheduler_loop())
    yield
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        logger.info("爬虫定时采集调度器已停止")


app = FastAPI(
    title="CPublic Sentiment",
    description="Enterprise public sentiment risk early warning multi-agent system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "env": settings.app_env}
