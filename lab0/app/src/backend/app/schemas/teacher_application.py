from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class TeacherApplicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    contact_method: Literal["telegram", "max", "phone", "email"]
    contact_value: str = Field(min_length=3, max_length=255)
    subjects: str = Field(min_length=2, max_length=500)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "contact_value", "subjects")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_contact(self):
        if self.contact_method == "email" and ("@" not in self.contact_value or "." not in self.contact_value.rsplit("@", 1)[-1]):
            raise ValueError("Укажите корректную почту")
        if self.contact_method == "phone":
            digits = "".join(character for character in self.contact_value if character.isdigit())
            if len(digits) < 10:
                raise ValueError("Укажите корректный номер телефона")
        return self


class TeacherApplicationRead(BaseModel):
    id: int
    name: str
    contact_method: str
    contact_value: str
    subjects: str
    note: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

