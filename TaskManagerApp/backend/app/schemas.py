"""Pydantic request/response schemas (the API contract)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import TaskStatus


# --------------------------------------------------------------------------- #
# Users / auth
# --------------------------------------------------------------------------- #
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=150)
    last_name: str = Field(min_length=1, max_length=150)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)
    manager_id: int | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    manager_id: int | None = None
    full_name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


# --------------------------------------------------------------------------- #
# Comments
# --------------------------------------------------------------------------- #
class CommentCreate(BaseModel):
    content: str = Field(min_length=1)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    content: str
    created_by: int
    created_at: datetime
    author: str


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
class TaskBase(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    deadline: date
    status: TaskStatus = TaskStatus.pending
    assigned_user_id: int


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    deadline: date | None = None
    status: TaskStatus | None = None
    assigned_user_id: int | None = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: str
    assigned_user_name: str
    comment_count: int
    can_edit: bool = False
