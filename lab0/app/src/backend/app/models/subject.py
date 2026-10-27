from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    exam_type: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    price_month: Mapped[int] = mapped_column(Integer)
    icon: Mapped[str] = mapped_column(String(40), default="book")
    tint: Mapped[str] = mapped_column(String(40), default="peach")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    teachers = relationship("Teacher", back_populates="subject", cascade="all, delete-orphan")
    teacher_assignments = relationship("TeacherSubject", back_populates="subject", cascade="all, delete-orphan")
