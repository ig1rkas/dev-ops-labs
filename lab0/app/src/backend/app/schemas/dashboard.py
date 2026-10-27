from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StudentDashboardRead(BaseModel):
    id: int
    user_id: int
    summary: dict[str, Any]
    stats: list[dict[str, Any]]
    courses: list[dict[str, Any]]
    lessons: list[dict[str, Any]]
    homework: list[dict[str, Any]]
    achievements: list[dict[str, Any]]
    settings: dict[str, Any]
    recommendation: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudentDashboardSettingsUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=140)
    notifications: bool | None = None
    weekly_digest: bool | None = None
    lesson_reminders: bool | None = None
    timezone: str | None = Field(default=None, min_length=3, max_length=64)

class TeacherDashboardRead(BaseModel):
    summary: dict[str, Any]
    stats: list[dict[str, Any]]
    courses: list[dict[str, Any]]
    lessons: list[dict[str, Any]]
    students: list[dict[str, Any]]
    settings: dict[str, Any]
    teacher: dict[str, Any] | None = None
