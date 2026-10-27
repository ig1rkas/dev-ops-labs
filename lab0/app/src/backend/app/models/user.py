from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(140))
    role: Mapped[str] = mapped_column(String(24), index=True)
    password_hash: Mapped[str] = mapped_column(String(260))
    # Telegram contacts are kept on the student account as a stable link to
    # incoming messages.  A user can be created automatically from a message
    # or manually by an administrator.
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")
    student_dashboard = relationship("StudentDashboard", back_populates="user", cascade="all, delete-orphan", uselist=False)
    chat_participants = relationship("ChatParticipant", back_populates="user")
    chat_messages = relationship("ChatMessage", back_populates="sender")
