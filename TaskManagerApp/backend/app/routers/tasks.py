"""Task CRUD, visibility scoping, and filtering.

Visibility (ported from the original ``api_getTasks``): a user sees tasks they
created, tasks assigned to them, and tasks created by anyone below them in the
org hierarchy. Filters run *within* that visible set.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Task, TaskStatus, User
from ..permissions import can_edit_task, subordinate_ids
from ..schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _serialize(db: Session, task: Task, user: User) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        status=task.status,
        assigned_user_id=task.assigned_user_id,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        creator_name=task.creator.full_name if task.creator else "",
        assigned_user_name=task.assigned_user.full_name if task.assigned_user else "",
        comment_count=len(task.comments),
        can_edit=can_edit_task(db, task, user),
    )


def _visible_tasks(db: Session, user: User) -> list[Task]:
    subs = subordinate_ids(db, user.id)
    stmt = (
        select(Task)
        .where(
            Task.created_by.in_(subs) | (Task.assigned_user_id == user.id)
        )
        .order_by(Task.created_at.desc())
    )
    return list(db.scalars(stmt).unique().all())


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sort: Literal["created", "deadline"] = "created",
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    created_by: int | None = None,
    assigned_to: int | None = None,
    managed: Literal["created", "assigned"] | None = None,
):
    tasks = _visible_tasks(db, current_user)

    if status_filter is not None:
        tasks = [t for t in tasks if t.status == status_filter]
    if created_by is not None:
        tasks = [t for t in tasks if t.created_by == created_by]
    if assigned_to is not None:
        tasks = [t for t in tasks if t.assigned_user_id == assigned_to]
    if managed == "created":
        tasks = [t for t in tasks if t.creator and t.creator.manager_id is not None]
    elif managed == "assigned":
        tasks = [
            t
            for t in tasks
            if t.assigned_user and t.assigned_user.manager_id is not None
        ]

    if sort == "deadline":
        tasks.sort(key=lambda t: t.deadline, reverse=True)
    else:
        tasks.sort(key=lambda t: t.created_at, reverse=True)

    return [_serialize(db, t, current_user) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return _serialize(db, task, current_user)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.get(User, payload.assigned_user_id) is None:
        raise HTTPException(status_code=422, detail="Assigned user does not exist.")

    task = Task(
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        status=payload.status,
        assigned_user_id=payload.assigned_user_id,
        created_by=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _serialize(db, task, current_user)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    if not can_edit_task(db, task, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this task.",
        )

    data = payload.model_dump(exclude_unset=True)
    if "assigned_user_id" in data and db.get(User, data["assigned_user_id"]) is None:
        raise HTTPException(status_code=422, detail="Assigned user does not exist.")
    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return _serialize(db, task, current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    if not can_edit_task(db, task, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this task.",
        )
    db.delete(task)
    db.commit()
