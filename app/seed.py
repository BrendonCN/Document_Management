from __future__ import annotations

import sqlite3

from app import repo
from app.db import connect, init_schema
from app.services.tree import create_node


SEED_USERS = [
    {"username": "admin", "display_name": "Admin User", "role": "admin"},
    {"username": "editor", "display_name": "Editor User", "role": "editor"},
    {"username": "viewer", "display_name": "Viewer User", "role": "viewer"},
]


def seed_users(db: sqlite3.Connection) -> None:
    for spec in SEED_USERS:
        existing = repo.get_user_by_username(db, spec["username"])
        if existing is None:
            repo.insert_user(
                db,
                username=spec["username"],
                display_name=spec["display_name"],
                role=spec["role"],
                is_active=True,
            )
    db.commit()


def seed_sample_tree(db: sqlite3.Connection) -> None:
    if repo.count_nodes(db) > 0:
        return
    admin = repo.get_user_by_username(db, "admin")
    if not admin:
        return

    root = create_node(db, admin, name="Documents", kind="folder", parent_id=None)
    create_node(db, admin, name="Welcome.txt", kind="txt", parent_id=root.id)
    create_node(db, admin, name="Notes.md", kind="md", parent_id=root.id)
    projects = create_node(db, admin, name="Projects", kind="folder", parent_id=root.id)
    create_node(db, admin, name="Plan.docx", kind="docx", parent_id=projects.id)
    create_node(db, admin, name="Budget.xlsx", kind="xlsx", parent_id=projects.id)


def init_db() -> None:
    init_schema()
    db = connect()
    try:
        seed_users(db)
        seed_sample_tree(db)
    finally:
        db.close()
