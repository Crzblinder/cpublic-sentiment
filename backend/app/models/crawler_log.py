from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class CrawlerLog(Base):
    __tablename__ = "crawler_logs"

    id = Column(Integer, primary_key=True, index=True)
    fetched = Column(Integer, default=0)
    cleaned = Column(Integer, default=0)
    persisted = Column(Integer, default=0)
    deduped = Column(Integer, default=0)
    sources_ok = Column(String(1024), default="")
    sources_failed = Column(String(1024), default="")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
