from __future__ import annotations

import difflib
import io
import json
import sqlite3
from typing import Any, Optional

from app import repo
from app.models import Node, User, Version
from app.services import storage
from app.services.audit import record_audit
from app.services.versions import copy_version


def load_text_content(version: Version) -> str:
    kind_hint = version.filename.lower()
    path = storage.resolve_storage_path(version.storage_path)
    if not path.exists():
        return ""

    if kind_hint.endswith(".docx") or version.content_type and "wordprocessingml" in (version.content_type or ""):
        return _docx_to_html(path.read_bytes())
    if kind_hint.endswith((".txt", ".md")) or (version.content_type or "").startswith("text/"):
        return path.read_text(encoding="utf-8", errors="replace")
    if kind_hint.endswith(".xlsx"):
        return json.dumps(load_spreadsheet(version), indent=2)
    return path.read_text(encoding="utf-8", errors="replace")


def _docx_to_html(data: bytes) -> str:
    try:
        import mammoth

        result = mammoth.convert_to_html(io.BytesIO(data))
        return result.value or ""
    except Exception:
        try:
            from docx import Document

            doc = Document(io.BytesIO(data))
            parts = []
            for p in doc.paragraphs:
                parts.append(f"<p>{_escape(p.text)}</p>")
            return "\n".join(parts) if parts else "<p></p>"
        except Exception:
            return "<p></p>"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _html_to_docx(html: str) -> bytes:
    from docx import Document
    from bs4 import BeautifulSoup

    doc = Document()
    soup = BeautifulSoup(html or "", "html.parser")
    # Clear default empty paragraph if we will add content
    body_text_blocks = soup.find_all(["p", "h1", "h2", "h3", "h4", "li", "div"])
    if not body_text_blocks:
        text = soup.get_text("\n")
        for line in text.splitlines() or [""]:
            doc.add_paragraph(line)
    else:
        # Remove the initial empty paragraph
        if doc.paragraphs:
            p0 = doc.paragraphs[0]
            p0.clear()
        first = True
        for el in body_text_blocks:
            text = el.get_text(strip=False)
            style = None
            if el.name == "h1":
                style = "Heading 1"
            elif el.name == "h2":
                style = "Heading 2"
            elif el.name == "h3":
                style = "Heading 3"
            if first and doc.paragraphs and not doc.paragraphs[0].text:
                if style:
                    doc.paragraphs[0].style = style
                doc.paragraphs[0].add_run(text)
                first = False
            else:
                doc.add_paragraph(text, style=style)
                first = False
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def save_text_content(
    db: sqlite3.Connection,
    node: Node,
    version: Version,
    user: User,
    content: str,
    *,
    create_new_version: bool = False,
    version_label: Optional[str] = None,
) -> Version:
    target = version
    if create_new_version:
        target = copy_version(db, node, version, user, label=version_label)

    fname = target.filename
    if node.kind == "docx" or fname.endswith(".docx"):
        data = _html_to_docx(content)
        storage.write_bytes(node.id, target.id, fname, data)
    elif node.kind in {"txt", "md", "folder"} or fname.endswith((".txt", ".md")):
        storage.write_text(node.id, target.id, fname, content)
    else:
        storage.write_text(node.id, target.id, fname, content)

    record_audit(
        db,
        user=user,
        action="content.save",
        node=node,
        detail={"version_id": target.id, "new_version": create_new_version},
    )
    db.commit()
    return repo.get_version(db, target.id) or target


def load_spreadsheet(version: Version) -> dict[str, list[list[Any]]]:
    from openpyxl import load_workbook

    path = storage.resolve_storage_path(version.storage_path)
    if not path.exists():
        return {"Sheet": [[""]]}
    wb = load_workbook(path)
    sheets: dict[str, list[list[Any]]] = {}
    for name in wb.sheetnames:
        ws = wb[name]
        rows: list[list[Any]] = []
        for row in ws.iter_rows(values_only=True):
            rows.append([("" if c is None else c) for c in row])
        if not rows:
            rows = [[""]]
        sheets[name] = rows
    return sheets


def save_spreadsheet(
    db: sqlite3.Connection,
    node: Node,
    version: Version,
    user: User,
    sheets: dict[str, list[list[Any]]],
    *,
    create_new_version: bool = False,
    version_label: Optional[str] = None,
) -> Version:
    from openpyxl import Workbook

    target = version
    if create_new_version:
        target = copy_version(db, node, version, user, label=version_label)

    wb = Workbook()
    # remove default
    default = wb.active
    wb.remove(default)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name[:31] or "Sheet")
        for r_idx, row in enumerate(rows, start=1):
            for c_idx, val in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx, value=val)
    if not wb.sheetnames:
        wb.create_sheet("Sheet")
    buf = io.BytesIO()
    wb.save(buf)
    storage.write_bytes(node.id, target.id, target.filename, buf.getvalue())
    record_audit(
        db,
        user=user,
        action="content.save",
        node=node,
        detail={"version_id": target.id, "kind": "xlsx"},
    )
    db.commit()
    return repo.get_version(db, target.id) or target


def text_for_diff(version: Version, kind: str) -> str:
    path = storage.resolve_storage_path(version.storage_path)
    if not path.exists():
        return ""
    if kind == "docx" or version.filename.endswith(".docx"):
        html = _docx_to_html(path.read_bytes())
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser").get_text("\n")
    if kind == "xlsx" or version.filename.endswith(".xlsx"):
        sheets = load_spreadsheet(version)
        lines = []
        for name, rows in sheets.items():
            lines.append(f"## {name}")
            for row in rows:
                lines.append("\t".join(str(c) for c in row))
        return "\n".join(lines)
    return path.read_text(encoding="utf-8", errors="replace")


def compute_diff(left: Version, right: Version, kind: str) -> dict[str, Any]:
    left_text = text_for_diff(left, kind)
    right_text = text_for_diff(right, kind)
    left_lines = left_text.splitlines()
    right_lines = right_text.splitlines()
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines)
    opcodes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        opcodes.append(
            {
                "tag": tag,
                "left_start": i1,
                "left_end": i2,
                "right_start": j1,
                "right_end": j2,
                "left_lines": left_lines[i1:i2],
                "right_lines": right_lines[j1:j2],
            }
        )
    return {
        "left_lines": left_lines,
        "right_lines": right_lines,
        "opcodes": opcodes,
        "left_version_id": left.id,
        "right_version_id": right.id,
    }


def apply_diff_line(
    db: sqlite3.Connection,
    node: Node,
    left: Version,
    right: Version,
    user: User,
    *,
    direction: str,
    line_index: int,
) -> dict[str, Any]:
    """Overwrite a single line from one side to the other (IntelliJ-style)."""
    left_lines = text_for_diff(left, node.kind).splitlines()
    right_lines = text_for_diff(right, node.kind).splitlines()

    if direction == "to_right":
        if line_index < 0 or line_index >= len(left_lines):
            raise ValueError("Invalid line index")
        while len(right_lines) <= line_index:
            right_lines.append("")
        right_lines[line_index] = left_lines[line_index]
        new_text = "\n".join(right_lines)
        target = right
    else:
        if line_index < 0 or line_index >= len(right_lines):
            raise ValueError("Invalid line index")
        while len(left_lines) <= line_index:
            left_lines.append("")
        left_lines[line_index] = right_lines[line_index]
        new_text = "\n".join(left_lines)
        target = left

    # Persist as text for diff-friendly kinds; for docx wrap as paragraphs
    if node.kind == "docx":
        html = "".join(f"<p>{_escape(line)}</p>" for line in new_text.splitlines())
        save_text_content(db, node, target, user, html)
    elif node.kind == "xlsx":
        # store as single-sheet TSV rebuild
        rows = [line.split("\t") for line in new_text.splitlines()]
        save_spreadsheet(db, node, target, user, {"Sheet": rows or [[""]]})
    else:
        save_text_content(db, node, target, user, new_text)

    record_audit(
        db,
        user=user,
        action="diff.apply_line",
        node=node,
        detail={"direction": direction, "line_index": line_index, "target_version": target.id},
    )
    return compute_diff(left, right, node.kind)
