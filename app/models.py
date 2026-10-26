from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


def parse_dt(value: datetime | str | None) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    return datetime.fromisoformat(text)


def format_dt(value: datetime | None) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat(sep=" ")


def parse_bool(value: bool | int | str | None) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes"}


def format_bool(value: bool) -> int:
    return 1 if value else 0


@dataclass
class User:
    id: int
    username: str
    display_name: str
    role: str
    last_login_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> User:
        return cls(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            role=row["role"],
            last_login_at=parse_dt(row["last_login_at"]),
            is_active=parse_bool(row["is_active"]),
            created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        )


@dataclass
class SessionRecord:
    id: str
    user_id: int
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> SessionRecord:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
            expires_at=parse_dt(row["expires_at"]) or datetime.utcnow(),
        )


@dataclass
class Node:
    id: int
    parent_id: Optional[int]
    name: str
    kind: str
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    sort_order: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Node:
        return cls(
            id=row["id"],
            parent_id=row["parent_id"],
            name=row["name"],
            kind=row["kind"],
            created_by=row["created_by"],
            created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
            updated_at=parse_dt(row["updated_at"]) or datetime.utcnow(),
            sort_order=row["sort_order"],
        )


@dataclass
class Version:
    id: int
    node_id: int
    version_label: str
    version_date: datetime
    storage_path: str
    created_by: Optional[int]
    created_at: datetime
    ordinal: int
    filename: str
    content_type: Optional[str]

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Version:
        return cls(
            id=row["id"],
            node_id=row["node_id"],
            version_label=row["version_label"],
            version_date=parse_dt(row["version_date"]) or datetime.utcnow(),
            storage_path=row["storage_path"],
            created_by=row["created_by"],
            created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
            ordinal=row["ordinal"],
            filename=row["filename"],
            content_type=row["content_type"],
        )


@dataclass
class AuditEvent:
    id: int
    user_id: Optional[int]
    username: str
    action: str
    node_id: Optional[int]
    path_snapshot: str
    detail_json: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> AuditEvent:
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            action=row["action"],
            node_id=row["node_id"],
            path_snapshot=row["path_snapshot"],
            detail_json=row["detail_json"],
            created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        )
