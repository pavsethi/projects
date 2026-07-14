"""Org-hierarchy permission logic, ported from the original controllers.

The py4web app decided task visibility and edit rights from a management chain
built on ``auth_user.manager_id``. These helpers reproduce that behaviour:

- ``subordinate_ids`` collects a user plus everyone below them in the tree,
  matching the recursive ``get_all_subordinates`` in the original api_getTasks.
- ``can_edit_task`` grants edit to the task creator, anyone in the creator's
  management chain, or the admin (the first-registered user).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Task, User


def subordinate_ids(db: Session, user_id: int) -> set[int]:
    """Return ``user_id`` plus the ids of all users below them in the org tree."""
    result: set[int] = set()
    stack = [user_id]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        direct = db.scalars(
            select(User.id).where(User.manager_id == current)
        ).all()
        stack.extend(direct)
    return result


def _admin_id(db: Session) -> int | None:
    """The first-registered user acts as the admin (as in the original app)."""
    return db.scalar(select(User.id).order_by(User.id).limit(1))


def can_edit_task(db: Session, task: Task, user: User) -> bool:
    if task.created_by == user.id:
        return True
    if _admin_id(db) == user.id:
        return True
    # Walk up the creator's management chain; the current user may edit if they
    # manage the creator at any level.
    creator = db.get(User, task.created_by)
    seen: set[int] = set()
    while creator is not None and creator.manager_id is not None:
        if creator.manager_id in seen:  # guard against cycles
            break
        seen.add(creator.manager_id)
        if creator.manager_id == user.id:
            return True
        creator = db.get(User, creator.manager_id)
    return False
