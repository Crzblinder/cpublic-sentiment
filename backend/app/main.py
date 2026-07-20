import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  注册所有模型到 Base.metadata
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
    yield


app = FastAPI(
    title="岗位技能图谱与人才匹配引擎",
    description="Skill map and talent matching engine",
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
