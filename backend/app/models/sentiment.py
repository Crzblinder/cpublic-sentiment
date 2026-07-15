from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class SentimentEvent(Base):
    __tablename__ = "sentiment_events"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(128), unique=True, nullable=True, index=True)
    title = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(128), nullable=False, index=True)
    url = Column(String(1024), nullable=True)
    # Matched enterprise
    enterprise_id = Column(Integer, nullable=True, index=True)
    enterprise_name = Column(String(255), nullable=True, index=True)
    # Risk fields
    risk_level = Column(String(32), nullable=True, index=True)
    risk_type = Column(String(128), nullable=True, index=True)
    risk_score = Column(Float, default=0.0)
    # Agent outputs
    matched_case_ids = Column(JSON, default=list)
    governance_plan = Column(JSON, default=dict)
    reasoning_chain = Column(JSON, default=list)
    # Evaluation / feedback
    labeled_risk_level = Column(String(32), nullable=True)
    is_correct = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    prompt_variant = Column(String(64), nullable=True, index=True)
    # Lifecycle
    status = Column(String(32), default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
