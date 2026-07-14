"""Comment listing and creation for a task."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Comment, Task, User
from ..schemas import CommentCreate, CommentOut

router = APIRouter(prefix="/api/tasks/{task_id}/comments", tags=["comments"])


def _serialize(comment: Comment) -> CommentOut:
    return CommentOut(
        id=comment.id,
        task_id=comment.task_id,
        content=comment.content,
        created_by=comment.created_by,
        created_at=comment.created_at,
        author=comment.author.full_name if comment.author else "",
    )


@router.get("", response_model=list[CommentOut])
def list_comments(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return [_serialize(c) for c in task.comments]


@router.post("", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    task_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    comment = Comment(
        task_id=task_id,
        content=payload.content,
        created_by=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _serialize(comment)
