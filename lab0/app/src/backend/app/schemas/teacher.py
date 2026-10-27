from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TeacherRead(BaseModel):
    id: int
    name: str
    role: str
    description: str
    rating: Decimal
    initials: str
    subject_id: int
    subject_title: str
    subject_slug: str
    category: str
    categories: list[str] = []
    subjects: list[dict] = []
    lesson_price: int
    avatar_url: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
