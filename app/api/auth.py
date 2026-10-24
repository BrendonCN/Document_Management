from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_user
from app.auth.provider import get_auth_provider
from app.config import SESSION_COOKIE, SESSION_MAX_AGE
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, Message, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user, session_id = get_auth_provider().login(
            db,
            username=payload.username,
            role=payload.role,
            display_name=payload.display_name,
            create_if_missing=payload.create_if_missing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
    )
    return user


@router.post("/logout", response_model=Message)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    _ = user
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        get_auth_provider().logout(db, session_id)
    response.delete_cookie(SESSION_COOKIE)
    return Message(message="Logged out")


@router.get("/me", response_model=UserOut | None)
def me(user: User | None = Depends(get_current_user)):
    return user
