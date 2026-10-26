from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import repo
from app.auth.deps import require_roles
from app.db import get_db
from app.models import User
from app.schemas import Message, UserCreate, UserOut, UserUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    return repo.list_users(db)


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    username = payload.username.strip().lower()
    if repo.get_user_by_username(db, username):
        raise HTTPException(status_code=400, detail="Username already exists")
    user = repo.insert_user(
        db,
        username=username,
        display_name=payload.display_name.strip(),
        role=payload.role,
        is_active=True,
    )
    record_audit(
        db,
        user=admin,
        action="user.create",
        detail={"username": username, "role": payload.role},
    )
    db.commit()
    return repo.get_user(db, user.id) or user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    user = repo.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    repo.update_user(db, user)
    record_audit(
        db,
        user=admin,
        action="user.update",
        detail={"user_id": user_id, **payload.model_dump(exclude_none=True)},
    )
    db.commit()
    return repo.get_user(db, user.id) or user


@router.delete("/{user_id}", response_model=Message)
def delete_user(
    user_id: int,
    db: sqlite3.Connection = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    user = repo.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    record_audit(
        db,
        user=admin,
        action="user.delete",
        detail={"user_id": user_id, "username": user.username},
    )
    repo.delete_user(db, user_id)
    db.commit()
    return Message(message="User deleted")
