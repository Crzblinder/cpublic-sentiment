from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class RiskCase(Base):
    __tablename__ = "risk_cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    industry = Column(String(128), nullable=False, index=True)
    risk_type = Column(String(128), nullable=False, index=True)
    risk_level = Column(String(32), nullable=False, index=True)
    source_url = Column(String(1024), nullable=True)
    tags = Column(JSON, default=list)
    # Structured governance playbook attached to each case
    governance_playbook = Column(JSON, default=dict)
    vector_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Optimized filters for RAG retrieval
        {"mysql_engine": "InnoDB"},
    )
