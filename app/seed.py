from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import User
from app.services.tree import create_node


SEED_USERS = [
    {"username": "admin", "display_name": "Admin User", "role": "admin"},
    {"username": "editor", "display_name": "Editor User", "role": "editor"},
    {"username": "viewer", "display_name": "Viewer User", "role": "viewer"},
]


def seed_users(db: Session) -> None:
    for spec in SEED_USERS:
        existing = db.query(User).filter(User.username == spec["username"]).first()
        if existing is None:
            db.add(User(**spec, is_active=True))
    db.commit()


def seed_sample_tree(db: Session) -> None:
    from app.models import Node

    if db.query(Node).count() > 0:
        return
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        return

    root = create_node(db, admin, name="Documents", kind="folder", parent_id=None)
    create_node(db, admin, name="Welcome.txt", kind="txt", parent_id=root.id)
    create_node(db, admin, name="Notes.md", kind="md", parent_id=root.id)
    projects = create_node(db, admin, name="Projects", kind="folder", parent_id=root.id)
    create_node(db, admin, name="Plan.docx", kind="docx", parent_id=projects.id)
    create_node(db, admin, name="Budget.xlsx", kind="xlsx", parent_id=projects.id)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
        seed_sample_tree(db)
    finally:
        db.close()
