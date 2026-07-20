from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class UserSkillProfile(Base):
    __tablename__ = "user_skill_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    skills = Column(Text, nullable=False, default="[]")
    experience_level = Column(String(64), nullable=False)
    target_job_titles = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
