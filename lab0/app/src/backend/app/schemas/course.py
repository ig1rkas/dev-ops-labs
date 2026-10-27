from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CourseRead(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    description: str
    price_month: int
    rating: Decimal
    lessons_count: int
    accent_color: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
