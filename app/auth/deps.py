from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.provider import get_auth_provider
from app.db import get_db
from app.models import User


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    session_id = request.cookies.get("dm_session")
    return get_auth_provider().resolve_user(db, session_id)


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_roles(*roles: str) -> Callable:
    def _dep(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return user

    return _dep


def can_mutate(user: User) -> bool:
    return user.role in {"admin", "editor"}


def can_admin(user: User) -> bool:
    return user.role == "admin"
