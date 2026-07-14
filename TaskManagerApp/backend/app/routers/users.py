"""User listing, used to populate assignee / manager pickers in the UI.

The registration form needs the list of possible managers *before* the user is
authenticated, so listing is public (it exposes only names, not credentials).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.first_name, User.last_name)).all()
