from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_histories"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    scan_result = Column(JSON, default=dict)
    matched_cases = Column(JSON, default=list)
    enterprise = Column(JSON, nullable=True)
    prediction = Column(JSON, default=dict)
    governance = Column(JSON, default=dict)
    reasoning_chain = Column(JSON, default=list)
    risk_level = Column(String(32), nullable=True, index=True)
    risk_type = Column(String(128), nullable=True, index=True)
    risk_score = Column(String(32), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
