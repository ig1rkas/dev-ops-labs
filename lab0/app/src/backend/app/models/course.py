from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    price_month: Mapped[int] = mapped_column(Integer)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=4.9)
    lessons_count: Mapped[int] = mapped_column(Integer, default=12)
    accent_color: Mapped[str] = mapped_column(String(24), default="#f04a23")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
