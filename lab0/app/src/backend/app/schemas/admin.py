from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminDashboardRead(BaseModel):
    summary: dict[str, Any]
    stats: list[dict[str, Any]]


class AdminUserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    telegram_user_id: int | None = None
    telegram_username: str | None = None
    created_at: datetime
    password_status: str
    password_note: str
    teacher_profile: "AdminTeacherProfileRead | None" = None


class AdminTeacherProfileRead(BaseModel):
    id: int
    name: str
    role: str
    description: str
    rating: float
    initials: str
    subject_id: int
    subject_title: str
    subject_slug: str
    subjects: list[dict] = []
    categories: list[str] = []
    lesson_price: int
    avatar_url: str | None = None
    calendar_url: str | None = None
    sort_order: int = 0


class AdminTeacherCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=140)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(min_length=2, max_length=140)
    description: str = Field(min_length=2, max_length=4000)
    subject_slug: str | None = Field(default=None, max_length=120)
    subject_slugs: list[str] = Field(default_factory=list, max_length=30)
    initials: str | None = Field(default=None, max_length=8)
    rating: float = Field(default=4.9, ge=0, le=9.9)
    lesson_price: int = Field(default=1500, ge=0, le=10_000_000)
    avatar_url: str | None = Field(default=None, max_length=2_000_000)
    calendar_url: str | None = Field(default=None, max_length=4096)


class AdminTeacherUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=140)
    role: str = Field(min_length=2, max_length=140)
    description: str = Field(min_length=2, max_length=4000)
    subject_slugs: list[str] = Field(default_factory=list, max_length=30)
    initials: str | None = Field(default=None, max_length=8)
    rating: float = Field(default=4.9, ge=0, le=9.9)
    lesson_price: int = Field(default=1500, ge=0, le=10_000_000)
    avatar_url: str | None = Field(default=None, max_length=2_000_000)
    calendar_url: str | None = Field(default=None, max_length=4096)


class AdminTeacherReorder(BaseModel):
    action: Literal["first", "up", "down"]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class AdminStudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=140)
    telegram_user_id: int = Field(gt=0)
    telegram_username: str | None = Field(default=None, max_length=180)

    @field_validator("telegram_username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lstrip("@")
        return normalized or None


class AdminTeacherStudentCreate(BaseModel):
    student_id: int = Field(gt=0)


class AdminTeacherStudentRead(BaseModel):
    assignment_id: int
    teacher_user_id: int
    student_id: int
    student_name: str
    original_name: str
    display_name: str | None = None
    student_email: EmailStr
    telegram_user_id: int | None = None
    telegram_username: str | None = None
    subject_title: str


class TeacherStudentRead(BaseModel):
    assignment_id: int
    student_id: int
    student_name: str
    original_name: str
    display_name: str | None = None
    subject_title: str


class TeacherStudentDisplayNameUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=140)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
