from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.messaging import ChatDetailRead


class CourseRequestCreate(BaseModel):
    subject_slug: str = Field(min_length=2, max_length=120)
    teacher_id: int | None = Field(default=None, gt=0)
    contact_name: str = Field(min_length=2, max_length=140)
    contact_method: Literal["telegram", "max", "phone", "email"]
    contact_value: str = Field(min_length=3, max_length=255)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("contact_name", "contact_value")
    @classmethod
    def strip_contact_fields(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_contact(self):
        if self.contact_method == "email" and ("@" not in self.contact_value or "." not in self.contact_value.rsplit("@", 1)[-1]):
            raise ValueError("Укажите корректную почту")
        if self.contact_method == "phone":
            digits = "".join(character for character in self.contact_value if character.isdigit())
            if len(digits) < 10:
                raise ValueError("Укажите корректный номер телефона")
        return self


class CourseRequestRead(BaseModel):
    id: int
    status: str
    note: str | None
    student_id: int | None
    student_name: str
    student_email: str | None
    contact_name: str
    contact_method: str
    contact_value: str
    subject_id: int
    subject_slug: str
    subject_title: str
    teacher_id: int | None
    teacher_name: str | None
    chat_id: int | None
    created_at: datetime
    updated_at: datetime


class CourseRequestResponse(BaseModel):
    request: CourseRequestRead
    chat: ChatDetailRead | None = None


class ScheduleSlotCreate(BaseModel):
    weekday: int = Field(ge=0, le=6)
    time: str = Field(pattern=r"^\d{2}:\d{2}$")


class ScheduleLessonCreate(BaseModel):
    teacher_id: int
    starts_at: datetime | None = None
    slots: list[ScheduleSlotCreate] = Field(default_factory=list)
    duration_minutes: int = Field(default=60, ge=20, le=240)
    weeks_count: int = Field(default=12, ge=1, le=52)
    topic: str = Field(min_length=2, max_length=220)
