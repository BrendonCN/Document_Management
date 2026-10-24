from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from secrets import token_urlsafe
from typing import Optional

from sqlalchemy.orm import Session

from app.config import SESSION_MAX_AGE
from app.models import SessionRecord, User


class AuthProvider(ABC):
    """Seam for swapping stub SSO with real OIDC later."""

    @abstractmethod
    def login(
        self,
        db: Session,
        *,
        username: str,
        role: Optional[str] = None,
        display_name: Optional[str] = None,
        create_if_missing: bool = False,
    ) -> tuple[User, str]:
        """Authenticate and return (user, session_id)."""

    @abstractmethod
    def logout(self, db: Session, session_id: str) -> None:
        ...

    @abstractmethod
    def resolve_user(self, db: Session, session_id: Optional[str]) -> Optional[User]:
        ...


class StubAuthProvider(AuthProvider):
    """Local/dev SSO stub: pick or create a demo user and role."""

    def login(
        self,
        db: Session,
        *,
        username: str,
        role: Optional[str] = None,
        display_name: Optional[str] = None,
        create_if_missing: bool = False,
    ) -> tuple[User, str]:
        username = username.strip().lower()
        if not username:
            raise ValueError("Username is required")

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            if not create_if_missing:
                raise ValueError(f"Unknown user: {username}")
            user = User(
                username=username,
                display_name=display_name or username.title(),
                role=role or "viewer",
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            if role and role in {"admin", "editor", "viewer"}:
                user.role = role
            if display_name:
                user.display_name = display_name

        if not user.is_active:
            raise ValueError("User is inactive")

        user.last_login_at = datetime.utcnow()
        session_id = token_urlsafe(32)
        record = SessionRecord(
            id=session_id,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(seconds=SESSION_MAX_AGE),
        )
        db.add(record)
        db.commit()
        db.refresh(user)
        return user, session_id

    def logout(self, db: Session, session_id: str) -> None:
        record = db.get(SessionRecord, session_id)
        if record:
            db.delete(record)
            db.commit()

    def resolve_user(self, db: Session, session_id: Optional[str]) -> Optional[User]:
        if not session_id:
            return None
        record = db.get(SessionRecord, session_id)
        if not record:
            return None
        if record.expires_at < datetime.utcnow():
            db.delete(record)
            db.commit()
            return None
        user = db.get(User, record.user_id)
        if not user or not user.is_active:
            return None
        return user


_provider: AuthProvider = StubAuthProvider()


def get_auth_provider() -> AuthProvider:
    return _provider


def set_auth_provider(provider: AuthProvider) -> None:
    global _provider
    _provider = provider
