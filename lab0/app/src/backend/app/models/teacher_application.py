from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TeacherApplication(Base):
    __tablename__ = "teacher_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(140))
    contact_method: Mapped[str] = mapped_column(String(24))
    contact_value: Mapped[str] = mapped_column(String(255))
    subjects: Mapped[str] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

