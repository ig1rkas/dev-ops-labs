from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TelegramChat(Base):
    """A conversation belonging to the connected Telegram business account."""

    __tablename__ = "telegram_chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180), default="Telegram chat")
    username: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    chat_type: Mapped[str] = mapped_column(String(32), default="private")
    business_connection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("TelegramMessage", back_populates="chat", cascade="all, delete-orphan")


class TelegramIgnoredChat(Base):
    """A Telegram peer removed from the platform by an administrator.

    The Telegram conversation is deliberately not deleted remotely.  Keeping
    the peer id here prevents a future MTProto dialog/history sync from
    recreating the local chat after its student account was removed.
    """

    __tablename__ = "telegram_ignored_chats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelegramMessage(Base):
    __tablename__ = "telegram_messages"
    __table_args__ = (UniqueConstraint("chat_id", "telegram_message_id", name="uq_telegram_chat_message"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), index=True)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    sender_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    sender_name: Mapped[str] = mapped_column(String(180), default="Telegram user")
    sender_username: Mapped[str | None] = mapped_column(String(180), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(16), default="inbound", index=True)
    # NULL marks a legacy message whose media type has not been checked yet.
    has_photo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    has_document: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    document_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # JSON list of {emoji, count}; stored on the message so reactions survive restart.
    reactions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    chat = relationship("TelegramChat", back_populates="messages")
    photo = relationship("TelegramPhoto", back_populates="message", cascade="all, delete-orphan", uselist=False)
    document = relationship("TelegramDocument", back_populates="message", cascade="all, delete-orphan", uselist=False)


class TelegramPhoto(Base):
    """Cached image bytes, kept outside the frequently polled message rows."""

    __tablename__ = "telegram_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("telegram_messages.id", ondelete="CASCADE"), unique=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(32))
    data: Mapped[bytes] = mapped_column(LargeBinary)

    message = relationship("TelegramMessage", back_populates="photo")


class TelegramDocument(Base):
    """Downloaded files are cached after the first authorized request."""

    __tablename__ = "telegram_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("telegram_messages.id", ondelete="CASCADE"), unique=True, index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)

    message = relationship("TelegramMessage", back_populates="document")


class TelegramDeletedMessage(Base):
    """A locally deleted Telegram message that must not be imported again."""

    __tablename__ = "telegram_deleted_messages"
    __table_args__ = (UniqueConstraint("chat_id", "telegram_message_id", name="uq_telegram_deleted_chat_message"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), index=True)
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelegramChatReadState(Base):
    """Per-user read position for a Telegram conversation."""

    __tablename__ = "telegram_chat_read_states"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_telegram_chat_read_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("telegram_chats.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    last_read_message_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("telegram_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
