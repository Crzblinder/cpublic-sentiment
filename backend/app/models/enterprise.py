from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class Enterprise(Base):
    __tablename__ = "enterprises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(128), nullable=False, index=True)
    scale = Column(String(64), nullable=True)
    region = Column(String(128), nullable=True, index=True)
    business_tags = Column(JSON, default=list)
    risk_profile = Column(JSON, default=dict)
    risk_score_history = Column(JSON, default=list)
    # Pre-computed vector id in Chroma for fast retrieval
    vector_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        # Composite index supports industry + region filtering
        {"mysql_engine": "InnoDB"},
    )
