from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app import repo
from app.auth.deps import require_user
from app.db import get_db
from app.models import User
from app.schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    node_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    return repo.list_audit(db, node_id=node_id, limit=limit)
