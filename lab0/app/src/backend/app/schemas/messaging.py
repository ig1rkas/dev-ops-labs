from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRead(BaseModel):
    id: int
    title: str
    kind: str
    peer_names: list[str]
    last_message: str
    updated_at: datetime


class ChatMessageRead(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    sender_name: str
    sender_role: str
    body: str
    created_at: datetime
    is_mine: bool


class ChatDetailRead(BaseModel):
    chat: ChatRead
    messages: list[ChatMessageRead]


class ChatMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
