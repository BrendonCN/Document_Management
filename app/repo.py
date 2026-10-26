from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, TypeVar

from app.models import (
    AuditEvent,
    Node,
    SessionRecord,
    User,
    Version,
    format_bool,
    format_dt,
)

T = TypeVar("T")


def _one(conn: sqlite3.Connection, sql: str, params: tuple, cls: type[T]) -> Optional[T]:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return cls.from_row(row)  # type: ignore[attr-defined]


def _all(conn: sqlite3.Connection, sql: str, params: tuple, cls: type[T]) -> list[T]:
    return [cls.from_row(row) for row in conn.execute(sql, params).fetchall()]  # type: ignore[attr-defined]


def get_user(conn: sqlite3.Connection, user_id: int) -> Optional[User]:
    return _one(conn, "SELECT * FROM users WHERE id = ?", (user_id,), User)


def get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[User]:
    return _one(conn, "SELECT * FROM users WHERE username = ?", (username,), User)


def list_users(conn: sqlite3.Connection) -> list[User]:
    return _all(conn, "SELECT * FROM users ORDER BY username ASC", (), User)


def insert_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    display_name: str,
    role: str,
    is_active: bool = True,
    last_login_at: Optional[datetime] = None,
    created_at: Optional[datetime] = None,
) -> User:
    created = created_at or datetime.utcnow()
    cur = conn.execute(
        """
        INSERT INTO users (username, display_name, role, last_login_at, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            display_name,
            role,
            format_dt(last_login_at),
            format_bool(is_active),
            format_dt(created),
        ),
    )
    user = get_user(conn, int(cur.lastrowid))
    if user is None:
        raise RuntimeError("Failed to insert user")
    return user


def update_user(conn: sqlite3.Connection, user: User) -> None:
    conn.execute(
        """
        UPDATE users
        SET display_name = ?, role = ?, is_active = ?, last_login_at = ?
        WHERE id = ?
        """,
        (
            user.display_name,
            user.role,
            format_bool(user.is_active),
            format_dt(user.last_login_at),
            user.id,
        ),
    )


def delete_user(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def get_session(conn: sqlite3.Connection, session_id: str) -> Optional[SessionRecord]:
    return _one(conn, "SELECT * FROM sessions WHERE id = ?", (session_id,), SessionRecord)


def insert_session(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    user_id: int,
    expires_at: datetime,
    created_at: Optional[datetime] = None,
) -> SessionRecord:
    created = created_at or datetime.utcnow()
    conn.execute(
        """
        INSERT INTO sessions (id, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, user_id, format_dt(created), format_dt(expires_at)),
    )
    record = get_session(conn, session_id)
    if record is None:
        raise RuntimeError("Failed to insert session")
    return record


def delete_session(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def get_node(conn: sqlite3.Connection, node_id: int) -> Optional[Node]:
    return _one(conn, "SELECT * FROM nodes WHERE id = ?", (node_id,), Node)


def list_children(conn: sqlite3.Connection, parent_id: Optional[int]) -> list[Node]:
    if parent_id is None:
        sql = """
            SELECT * FROM nodes
            WHERE parent_id IS NULL
            ORDER BY sort_order ASC, name ASC
        """
        params: tuple = ()
    else:
        sql = """
            SELECT * FROM nodes
            WHERE parent_id = ?
            ORDER BY sort_order ASC, name ASC
        """
        params = (parent_id,)
    return _all(conn, sql, params, Node)


def count_children(conn: sqlite3.Connection, parent_id: Optional[int]) -> int:
    if parent_id is None:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM nodes WHERE parent_id IS NULL"
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM nodes WHERE parent_id = ?",
            (parent_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


def count_nodes(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM nodes").fetchone()
    return int(row["n"]) if row else 0


def search_nodes(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[Node]:
    pattern = f"%{query.strip()}%"
    return _all(
        conn,
        """
        SELECT * FROM nodes
        WHERE name LIKE ? COLLATE NOCASE
        ORDER BY name ASC
        LIMIT ?
        """,
        (pattern, limit),
        Node,
    )


def insert_node(
    conn: sqlite3.Connection,
    *,
    parent_id: Optional[int],
    name: str,
    kind: str,
    created_by: Optional[int],
    sort_order: int,
    created_at: Optional[datetime] = None,
) -> Node:
    now = created_at or datetime.utcnow()
    cur = conn.execute(
        """
        INSERT INTO nodes (parent_id, name, kind, created_by, created_at, updated_at, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (parent_id, name, kind, created_by, format_dt(now), format_dt(now), sort_order),
    )
    node = get_node(conn, int(cur.lastrowid))
    if node is None:
        raise RuntimeError("Failed to insert node")
    return node


def update_node_name(conn: sqlite3.Connection, node_id: int, name: str) -> None:
    conn.execute(
        "UPDATE nodes SET name = ?, updated_at = ? WHERE id = ?",
        (name, format_dt(datetime.utcnow()), node_id),
    )


def update_node_placement(
    conn: sqlite3.Connection,
    node_id: int,
    *,
    parent_id: Optional[int],
    sort_order: int,
) -> None:
    conn.execute(
        """
        UPDATE nodes
        SET parent_id = ?, sort_order = ?, updated_at = ?
        WHERE id = ?
        """,
        (parent_id, sort_order, format_dt(datetime.utcnow()), node_id),
    )


def delete_node(conn: sqlite3.Connection, node_id: int) -> None:
    conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))


def get_version(conn: sqlite3.Connection, version_id: int) -> Optional[Version]:
    return _one(conn, "SELECT * FROM versions WHERE id = ?", (version_id,), Version)


def list_versions(conn: sqlite3.Connection, node_id: int) -> list[Version]:
    return _all(
        conn,
        "SELECT * FROM versions WHERE node_id = ? ORDER BY ordinal ASC",
        (node_id,),
        Version,
    )


def get_latest_version(conn: sqlite3.Connection, node_id: int) -> Optional[Version]:
    return _one(
        conn,
        """
        SELECT * FROM versions
        WHERE node_id = ?
        ORDER BY ordinal DESC
        LIMIT 1
        """,
        (node_id,),
        Version,
    )


def count_versions(conn: sqlite3.Connection, node_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM versions WHERE node_id = ?",
        (node_id,),
    ).fetchone()
    return int(row["n"]) if row else 0


def insert_version(
    conn: sqlite3.Connection,
    *,
    node_id: int,
    version_label: str,
    version_date: datetime,
    storage_path: str,
    created_by: Optional[int],
    ordinal: int,
    filename: str,
    content_type: Optional[str],
    created_at: Optional[datetime] = None,
) -> Version:
    created = created_at or datetime.utcnow()
    cur = conn.execute(
        """
        INSERT INTO versions (
            node_id, version_label, version_date, storage_path, created_by,
            created_at, ordinal, filename, content_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            node_id,
            version_label,
            format_dt(version_date),
            storage_path,
            created_by,
            format_dt(created),
            ordinal,
            filename,
            content_type,
        ),
    )
    version = get_version(conn, int(cur.lastrowid))
    if version is None:
        raise RuntimeError("Failed to insert version")
    return version


def update_version_storage(conn: sqlite3.Connection, version_id: int, storage_path: str) -> None:
    conn.execute(
        "UPDATE versions SET storage_path = ? WHERE id = ?",
        (storage_path, version_id),
    )


def update_version_meta(
    conn: sqlite3.Connection,
    version_id: int,
    *,
    version_label: Optional[str] = None,
    version_date: Optional[datetime] = None,
) -> None:
    current = get_version(conn, version_id)
    if current is None:
        return
    label = current.version_label if version_label is None else version_label
    date = current.version_date if version_date is None else version_date
    conn.execute(
        "UPDATE versions SET version_label = ?, version_date = ? WHERE id = ?",
        (label, format_dt(date), version_id),
    )


def delete_version(conn: sqlite3.Connection, version_id: int) -> None:
    conn.execute("DELETE FROM versions WHERE id = ?", (version_id,))


def insert_audit(
    conn: sqlite3.Connection,
    *,
    user_id: Optional[int],
    username: str,
    action: str,
    node_id: Optional[int],
    path_snapshot: str,
    detail_json: str,
    created_at: Optional[datetime] = None,
) -> AuditEvent:
    created = created_at or datetime.utcnow()
    cur = conn.execute(
        """
        INSERT INTO audit_events (
            user_id, username, action, node_id, path_snapshot, detail_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, username, action, node_id, path_snapshot, detail_json, format_dt(created)),
    )
    event = _one(conn, "SELECT * FROM audit_events WHERE id = ?", (int(cur.lastrowid),), AuditEvent)
    if event is None:
        raise RuntimeError("Failed to insert audit event")
    return event


def list_audit(
    conn: sqlite3.Connection,
    *,
    node_id: Optional[int] = None,
    limit: int = 100,
) -> list[AuditEvent]:
    if node_id is None:
        sql = "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?"
        params: tuple = (limit,)
    else:
        sql = """
            SELECT * FROM audit_events
            WHERE node_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = (node_id, limit)
    return _all(conn, sql, params, AuditEvent)
