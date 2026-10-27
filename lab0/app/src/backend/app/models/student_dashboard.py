from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentDashboard(Base):
    __tablename__ = "student_dashboards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    summary: Mapped[dict] = mapped_column(JSON)
    stats: Mapped[list] = mapped_column(JSON)
    courses: Mapped[list] = mapped_column(JSON)
    lessons: Mapped[list] = mapped_column(JSON)
    homework: Mapped[list] = mapped_column(JSON)
    achievements: Mapped[list] = mapped_column(JSON)
    settings: Mapped[dict] = mapped_column(JSON)
    recommendation: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="student_dashboard")