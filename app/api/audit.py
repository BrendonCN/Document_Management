from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import require_user
from app.db import get_db
from app.models import AuditEvent, User
from app.schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    node_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
):
    q = db.query(AuditEvent).order_by(AuditEvent.created_at.desc())
    if node_id is not None:
        q = q.filter(AuditEvent.node_id == node_id)
    return q.limit(limit).all()
