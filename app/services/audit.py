from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditEvent, Node, User


def node_path(db: Session, node: Optional[Node]) -> str:
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
        current = db.get(Node, current.parent_id)
    return "/" + "/".join(reversed(parts))


def record_audit(
    db: Session,
    *,
    user: Optional[User],
    action: str,
    node: Optional[Node] = None,
    detail: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    event = AuditEvent(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        node_id=node.id if node else None,
        path_snapshot=node_path(db, node),
        detail_json=json.dumps(detail or {}, default=str),
    )
    db.add(event)
    db.flush()
    return event
