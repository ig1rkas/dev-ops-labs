from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["student", "teacher", "admin"]


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=140)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    role: UserRole | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserRead
