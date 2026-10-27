from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(140), index=True)
    role: Mapped[str] = mapped_column(String(140), index=True)
    description: Mapped[str] = mapped_column(Text)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=4.9)
    initials: Mapped[str] = mapped_column(String(8))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    lesson_price: Mapped[int] = mapped_column(Integer, nullable=False, default=1500, server_default="1500")
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Secret/public iCal feed configured by an administrator. It is never
    # included in the public teacher schema.
    calendar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Accounts created from the public teacher card use these fields so an
    # administrator can remove an account without it being recreated on the
    # next container restart.
    account_email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    account_disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subject = relationship("Subject", back_populates="teachers")
    subject_assignments = relationship("TeacherSubject", back_populates="teacher", cascade="all, delete-orphan")
