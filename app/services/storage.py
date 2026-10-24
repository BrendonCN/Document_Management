from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, Optional

from app.config import STORAGE_DIR


def version_dir(node_id: int, version_id: int) -> Path:
    path = STORAGE_DIR / str(node_id) / str(version_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_bytes(node_id: int, version_id: int, filename: str, data: bytes) -> str:
    dest = version_dir(node_id, version_id) / filename
    dest.write_bytes(data)
    return str(dest.relative_to(STORAGE_DIR.parent))


def write_stream(node_id: int, version_id: int, filename: str, stream: BinaryIO) -> str:
    dest = version_dir(node_id, version_id) / filename
    with dest.open("wb") as f:
        shutil.copyfileobj(stream, f)
    return str(dest.relative_to(STORAGE_DIR.parent))


def write_text(node_id: int, version_id: int, filename: str, text: str) -> str:
    return write_bytes(node_id, version_id, filename, text.encode("utf-8"))


def resolve_storage_path(storage_path: str) -> Path:
    """Resolve a relative storage path under data/."""
    from app.config import DATA_DIR

    path = Path(storage_path)
    if path.is_absolute():
        return path
    # storage_path is like "storage/1/2/file.docx" relative to data/
    candidate = DATA_DIR / path
    if candidate.exists():
        return candidate
    # also try relative to STORAGE_DIR parent
    return STORAGE_DIR.parent / path


def read_bytes(storage_path: str) -> bytes:
    return resolve_storage_path(storage_path).read_bytes()


def read_text(storage_path: str) -> str:
    return resolve_storage_path(storage_path).read_text(encoding="utf-8", errors="replace")


def copy_version_files(
    src_node_id: int,
    src_version_id: int,
    dest_node_id: int,
    dest_version_id: int,
    filename: Optional[str] = None,
) -> str:
    src = version_dir(src_node_id, src_version_id)
    dest = version_dir(dest_node_id, dest_version_id)
    if filename:
        src_file = src / filename
        if src_file.exists():
            shutil.copy2(src_file, dest / filename)
            return str((dest / filename).relative_to(STORAGE_DIR.parent))
    # copy all files
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dest / item.name)
            if filename is None:
                filename = item.name
    if not filename:
        filename = "content"
        (dest / filename).write_bytes(b"")
    return str((dest / filename).relative_to(STORAGE_DIR.parent))


def delete_node_storage(node_id: int) -> None:
    path = STORAGE_DIR / str(node_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def delete_version_storage(node_id: int, version_id: int) -> None:
    path = STORAGE_DIR / str(node_id) / str(version_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
