from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    city = Column(String(64), nullable=False, index=True)
    salary_min = Column(Integer, nullable=False)
    salary_max = Column(Integer, nullable=False)
    experience_level = Column(String(64), nullable=False, index=True)
    education_level = Column(String(32), nullable=False)
    required_skills = Column(Text, nullable=False, default="[]")
    description = Column(Text, nullable=False)
    posted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="jobs")
