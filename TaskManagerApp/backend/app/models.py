"""SQLAlchemy ORM models: User, Task, Comment.

These mirror the original py4web/pydal tables:
- auth_user (with a self-referential manager_id) -> User
- task (title, description, deadline, status, assigned_user) -> Task
- comment -> Comment

The original relied on pydal's ``auth.signature`` for created_by/created_on/
modified_by/modified_on audit fields; those are modelled explicitly here.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    pending = "pending"
    acknowledged = "acknowledged"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(150))
    last_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))

    # Self-referential org hierarchy: a user's manager is another user.
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    manager: Mapped[User | None] = relationship(
        remote_side=[id], backref="reports"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[date] = mapped_column(Date)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.pending
    )

    assigned_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_user: Mapped[User] = relationship(foreign_keys=[assigned_user_id])

    # Audit fields (equivalent to pydal's auth.signature).
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    comments: Mapped[list[Comment]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    content: Mapped[str] = mapped_column(Text)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped[User] = relationship(foreign_keys=[created_by])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    task: Mapped[Task] = relationship(back_populates="comments")
