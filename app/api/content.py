from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app import repo
from app.auth.deps import require_roles, require_user
from app.db import get_db
from app.models import User
from app.schemas import ContentSave, DiffApply, DiffRequest, SpreadsheetSave, VersionOut
from app.services import content as content_svc
from app.services import storage

router = APIRouter(tags=["content"])


@router.get("/versions/{version_id}/content")
def get_content(
    version_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    node = repo.get_node(db, version.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.kind == "xlsx":
        return {"kind": "xlsx", "sheets": content_svc.load_spreadsheet(version)}
    if node.kind in {"pdf", "object"}:
        return {
            "kind": node.kind,
            "filename": version.filename,
            "download_url": f"/api/versions/{version.id}/export",
            "open_url": f"/api/versions/{version.id}/open",
        }
    text = content_svc.load_text_content(version)
    return {"kind": node.kind, "content": text, "filename": version.filename}


@router.put("/versions/{version_id}/content", response_model=VersionOut)
def save_content(
    version_id: int,
    payload: ContentSave,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    node = repo.get_node(db, version.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.kind in {"pdf", "object"}:
        raise HTTPException(status_code=400, detail="Use import to replace binary content")
    if node.kind == "xlsx":
        raise HTTPException(status_code=400, detail="Use spreadsheet endpoint")
    saved = content_svc.save_text_content(
        db,
        node,
        version,
        user,
        payload.content,
        create_new_version=payload.create_new_version,
        version_label=payload.version_label,
    )
    return saved


@router.put("/versions/{version_id}/spreadsheet", response_model=VersionOut)
def save_spreadsheet(
    version_id: int,
    payload: SpreadsheetSave,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    node = repo.get_node(db, version.node_id)
    if not node or node.kind != "xlsx":
        raise HTTPException(status_code=400, detail="Not a spreadsheet node")
    saved = content_svc.save_spreadsheet(
        db,
        node,
        version,
        user,
        payload.sheets,
        create_new_version=payload.create_new_version,
        version_label=payload.version_label,
    )
    return saved


@router.get("/versions/{version_id}/open")
def open_binary(
    version_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    path = storage.resolve_storage_path(version.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(
        path,
        filename=version.filename,
        media_type=version.content_type or "application/octet-stream",
        content_disposition_type="inline",
    )


@router.post("/diff")
def diff_versions(
    payload: DiffRequest,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    left = repo.get_version(db, payload.left_version_id)
    right = repo.get_version(db, payload.right_version_id)
    if not left or not right:
        raise HTTPException(status_code=404, detail="Version not found")
    if left.node_id != right.node_id:
        raise HTTPException(status_code=400, detail="Versions must belong to same node")
    node = repo.get_node(db, left.node_id)
    return content_svc.compute_diff(left, right, node.kind if node else "txt")


@router.post("/diff/apply-line")
def apply_diff_line(
    payload: DiffApply,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    left = repo.get_version(db, payload.left_version_id)
    right = repo.get_version(db, payload.right_version_id)
    if not left or not right:
        raise HTTPException(status_code=404, detail="Version not found")
    if left.node_id != right.node_id:
        raise HTTPException(status_code=400, detail="Versions must belong to same node")
    node = repo.get_node(db, left.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        return content_svc.apply_diff_line(
            db,
            node,
            left,
            right,
            user,
            direction=payload.direction,
            line_index=payload.line_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
