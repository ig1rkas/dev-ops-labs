from datetime import datetime

from pydantic import BaseModel, Field


class TelegramChatRead(BaseModel):
    id: int
    telegram_chat_id: int | None = None
    title: str
    username: str | None = None
    chat_type: str
    last_message: str
    unread_count: int = 0
    updated_at: datetime


class TelegramReactionRead(BaseModel):
    emoji: str
    count: int = Field(ge=1)


class TelegramMessageRead(BaseModel):
    id: int
    telegram_message_id: int | None = None
    sender_name: str
    sender_username: str | None = None
    body: str
    has_photo: bool = False
    has_document: bool = False
    document_name: str | None = None
    reactions: list[TelegramReactionRead] = Field(default_factory=list)
    direction: str
    created_at: datetime
    telegram_date: datetime | None = None


class TelegramChatDetailRead(BaseModel):
    chat: TelegramChatRead
    messages: list[TelegramMessageRead]


class TelegramMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class TelegramStatusRead(BaseModel):
    configured: bool
    polling_enabled: bool
    running: bool
    mtproto_configured: bool = False
    mtproto_authorized: bool = False
    mtproto_running: bool = False
    mtproto_error: str | None = None
