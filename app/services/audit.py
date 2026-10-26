from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from app import repo
from app.models import AuditEvent, Node, User


def node_path(db: sqlite3.Connection, node: Optional[Node]) -> str:
    if node is None:
        return "/"
    parts: list[str] = []
    current: Optional[Node] = node
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        parts.append(current.name)
        if current.parent_id is None:
            break
        current = repo.get_node(db, current.parent_id)
    return "/" + "/".join(reversed(parts))


def record_audit(
    db: sqlite3.Connection,
    *,
    user: Optional[User],
    action: str,
    node: Optional[Node] = None,
    detail: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    return repo.insert_audit(
        db,
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        node_id=node.id if node else None,
        path_snapshot=node_path(db, node),
        detail_json=json.dumps(detail or {}, default=str),
    )
