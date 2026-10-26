from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import BinaryIO, Optional

from app import repo
from app.models import Node, User, Version
from app.services import storage
from app.services.audit import record_audit


KIND_DEFAULT_FILENAME = {
    "folder": "README.txt",
    "docx": "document.docx",
    "xlsx": "workbook.xlsx",
    "md": "document.md",
    "txt": "document.txt",
    "pdf": "document.pdf",
    "object": "object.bin",
}

KIND_CONTENT_TYPE = {
    "folder": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "md": "text/markdown",
    "txt": "text/plain",
    "pdf": "application/pdf",
    "object": "application/octet-stream",
}


def next_ordinal(db: sqlite3.Connection, node_id: int) -> int:
    last = repo.get_latest_version(db, node_id)
    return (last.ordinal + 1) if last else 1


def default_label(ordinal: int) -> str:
    # v 0.0.1, v 0.0.2, ... then bump minor every 10
    major = 0
    minor = (ordinal - 1) // 10
    patch = (ordinal - 1) % 10 + 1
    return f"v {major}.{minor}.{patch}"


def create_empty_version(
    db: sqlite3.Connection,
    node: Node,
    user: Optional[User],
    *,
    label: Optional[str] = None,
    initial_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> Version:
    ordinal = next_ordinal(db, node.id)
    fname = filename or KIND_DEFAULT_FILENAME.get(node.kind, "content")
    version = repo.insert_version(
        db,
        node_id=node.id,
        version_label=label or default_label(ordinal),
        version_date=datetime.utcnow(),
        storage_path="",
        created_by=user.id if user else None,
        ordinal=ordinal,
        filename=fname,
        content_type=KIND_CONTENT_TYPE.get(node.kind),
    )

    data = initial_bytes
    if data is None:
        data = _default_bytes(node.kind)
    rel = storage.write_bytes(node.id, version.id, fname, data)
    repo.update_version_storage(db, version.id, rel)
    version.storage_path = rel
    return version


def _default_bytes(kind: str) -> bytes:
    if kind == "txt":
        return b""
    if kind == "md":
        return b"# New Document\n\n"
    if kind == "folder":
        return b"Folder container\n"
    if kind == "docx":
        from io import BytesIO

        from docx import Document

        doc = Document()
        doc.add_paragraph("")
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
    if kind == "xlsx":
        from io import BytesIO

        from openpyxl import Workbook

        wb = Workbook()
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()
    if kind == "pdf":
        # Minimal valid PDF
        return (
            b"%PDF-1.4\n1 0 obj<<>>endobj\n"
            b"2 0 obj<< /Length 44 >>stream\nBT /F1 12 Tf 100 700 Td (Empty PDF) Tj ET\n"
            b"endstream\nendobj\ntrailer<<>>\n%%EOF\n"
        )
    return b""


def copy_version(
    db: sqlite3.Connection,
    node: Node,
    source: Version,
    user: Optional[User],
    *,
    label: Optional[str] = None,
) -> Version:
    ordinal = next_ordinal(db, node.id)
    version = repo.insert_version(
        db,
        node_id=node.id,
        version_label=label or default_label(ordinal),
        version_date=datetime.utcnow(),
        storage_path="",
        created_by=user.id if user else None,
        ordinal=ordinal,
        filename=source.filename,
        content_type=source.content_type,
    )
    rel = storage.copy_version_files(
        source.node_id, source.id, node.id, version.id, source.filename
    )
    repo.update_version_storage(db, version.id, rel)
    version.storage_path = rel
    record_audit(
        db,
        user=user,
        action="version.copy",
        node=node,
        detail={"from": source.id, "to": version.id, "label": version.version_label},
    )
    return version


def import_file(
    db: sqlite3.Connection,
    node: Node,
    user: Optional[User],
    *,
    filename: str,
    stream: BinaryIO,
    label: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Version:
    ordinal = next_ordinal(db, node.id)
    safe_name = Path_safe(filename)
    version = repo.insert_version(
        db,
        node_id=node.id,
        version_label=label or default_label(ordinal),
        version_date=datetime.utcnow(),
        storage_path="",
        created_by=user.id if user else None,
        ordinal=ordinal,
        filename=safe_name,
        content_type=content_type or KIND_CONTENT_TYPE.get(node.kind),
    )
    rel = storage.write_stream(node.id, version.id, safe_name, stream)
    repo.update_version_storage(db, version.id, rel)
    version.storage_path = rel
    record_audit(
        db,
        user=user,
        action="version.import",
        node=node,
        detail={"version_id": version.id, "filename": safe_name},
    )
    return version


def Path_safe(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").strip() or "content"


def get_current_version(db: sqlite3.Connection, node_id: int) -> Optional[Version]:
    return repo.get_latest_version(db, node_id)


def list_versions(db: sqlite3.Connection, node_id: int) -> list[Version]:
    return repo.list_versions(db, node_id)


def neighbor_versions(
    db: sqlite3.Connection, version: Version
) -> tuple[Optional[Version], Optional[Version]]:
    versions = list_versions(db, version.node_id)
    idx = next((i for i, v in enumerate(versions) if v.id == version.id), None)
    if idx is None:
        return None, None
    prev_v = versions[idx - 1] if idx > 0 else None
    next_v = versions[idx + 1] if idx < len(versions) - 1 else None
    return prev_v, next_v
