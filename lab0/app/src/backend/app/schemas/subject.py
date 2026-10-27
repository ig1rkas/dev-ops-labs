from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SubjectRead(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    exam_type: str | None
    description: str
    price_month: int
    icon: str
    tint: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminSubjectCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=60)
    exam_type: str | None = Field(default=None, max_length=20)
    description: str = Field(min_length=2, max_length=2000)
    price_month: int = Field(default=0, ge=0, le=10_000_000)
    icon: str = Field(default="book", min_length=1, max_length=40)
    tint: str = Field(default="peach", min_length=1, max_length=40)

    @field_validator("slug", "category", "icon", "tint", mode="before")
    @classmethod
    def strip_value(cls, value: str) -> str:
        return str(value).strip()
