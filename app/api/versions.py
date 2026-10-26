from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import repo
from app.auth.deps import require_roles, require_user
from app.db import get_db
from app.models import User
from app.schemas import Message, VersionCreate, VersionMetaUpdate, VersionOut
from app.services import storage
from app.services.audit import record_audit
from app.services.versions import (
    copy_version,
    get_current_version,
    import_file,
    list_versions,
    neighbor_versions,
)

router = APIRouter(tags=["versions"])


@router.get("/nodes/{node_id}/versions", response_model=list[VersionOut])
def get_versions(
    node_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    if not repo.get_node(db, node_id):
        raise HTTPException(status_code=404, detail="Node not found")
    return list_versions(db, node_id)


@router.get("/versions/{version_id}", response_model=VersionOut)
def get_version(
    version_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.get("/versions/{version_id}/neighbors")
def get_neighbors(
    version_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    prev_v, next_v = neighbor_versions(db, version)
    return {
        "prev": VersionOut.model_validate(prev_v) if prev_v else None,
        "next": VersionOut.model_validate(next_v) if next_v else None,
        "current": VersionOut.model_validate(version),
    }


@router.post("/nodes/{node_id}/versions", response_model=VersionOut)
def create_version(
    node_id: int,
    payload: VersionCreate,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    node = repo.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    source = None
    if payload.copy_from_version_id:
        source = repo.get_version(db, payload.copy_from_version_id)
        if not source or source.node_id != node_id:
            raise HTTPException(status_code=400, detail="Invalid source version")
    else:
        source = get_current_version(db, node_id)
    if not source:
        raise HTTPException(status_code=400, detail="No source version to copy")
    version = copy_version(db, node, source, user, label=payload.version_label)
    db.commit()
    return repo.get_version(db, version.id) or version


@router.patch("/versions/{version_id}", response_model=VersionOut)
def update_version_meta(
    version_id: int,
    payload: VersionMetaUpdate,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    node = repo.get_node(db, version.node_id)
    if payload.version_label is not None or payload.version_date is not None:
        repo.update_version_meta(
            db,
            version_id,
            version_label=payload.version_label,
            version_date=payload.version_date,
        )
    record_audit(
        db,
        user=user,
        action="version.meta_update",
        node=node,
        detail=payload.model_dump(exclude_none=True),
    )
    db.commit()
    return repo.get_version(db, version_id) or version


@router.delete("/versions/{version_id}", response_model=Message)
def delete_version(
    version_id: int,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    node = repo.get_node(db, version.node_id)
    remaining = repo.count_versions(db, version.node_id)
    if remaining <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only version")
    record_audit(
        db,
        user=user,
        action="version.delete",
        node=node,
        detail={"version_id": version_id, "label": version.version_label},
    )
    storage.delete_version_storage(version.node_id, version.id)
    repo.delete_version(db, version_id)
    db.commit()
    return Message(message="Version deleted")


@router.post("/nodes/{node_id}/import", response_model=VersionOut)
async def import_version(
    node_id: int,
    file: UploadFile = File(...),
    version_label: str | None = Form(None),
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    node = repo.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    version = import_file(
        db,
        node,
        user,
        filename=file.filename or "upload.bin",
        stream=file.file,
        label=version_label,
        content_type=file.content_type,
    )
    db.commit()
    return repo.get_version(db, version.id) or version


@router.get("/versions/{version_id}/export")
def export_version(
    version_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    version = repo.get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    path = storage.resolve_storage_path(version.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(
        path,
        filename=version.filename,
        media_type=version.content_type or "application/octet-stream",
    )
