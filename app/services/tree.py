from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import Node, User, Version
from app.schemas import NodeOut, TreeNodeOut
from app.services import storage
from app.services.audit import record_audit
from app.services.versions import create_empty_version, get_current_version


def node_to_out(db: Session, node: Node) -> NodeOut:
    current = get_current_version(db, node.id)
    count = db.query(Version).filter(Version.node_id == node.id).count()
    return NodeOut(
        id=node.id,
        parent_id=node.parent_id,
        name=node.name,
        kind=node.kind,  # type: ignore[arg-type]
        created_by=node.created_by,
        created_at=node.created_at,
        updated_at=node.updated_at,
        sort_order=node.sort_order,
        current_version_id=current.id if current else None,
        version_count=count,
    )


def build_tree(db: Session, parent_id: Optional[int] = None) -> list[TreeNodeOut]:
    nodes = (
        db.query(Node)
        .filter(Node.parent_id == parent_id)
        .order_by(Node.sort_order.asc(), Node.name.asc())
        .all()
    )
    result: list[TreeNodeOut] = []
    for node in nodes:
        base = node_to_out(db, node)
        result.append(
            TreeNodeOut(**base.model_dump(), children=build_tree(db, node.id))
        )
    return result


def create_node(
    db: Session,
    user: User,
    *,
    name: str,
    kind: str,
    parent_id: Optional[int] = None,
) -> Node:
    if parent_id is not None:
        parent = db.get(Node, parent_id)
        if parent is None:
            raise ValueError("Parent node not found")

    siblings = db.query(Node).filter(Node.parent_id == parent_id).count()
    node = Node(
        parent_id=parent_id,
        name=name.strip(),
        kind=kind,
        created_by=user.id,
        sort_order=siblings,
    )
    db.add(node)
    db.flush()

    if kind != "folder":
        create_empty_version(db, node, user)
    else:
        # folders may still hold a placeholder version for export uniformity
        create_empty_version(db, node, user)

    record_audit(
        db,
        user=user,
        action="node.create",
        node=node,
        detail={"kind": kind, "name": name},
    )
    db.commit()
    db.refresh(node)
    return node


def rename_node(db: Session, user: User, node: Node, name: str) -> Node:
    old = node.name
    node.name = name.strip()
    record_audit(
        db,
        user=user,
        action="node.rename",
        node=node,
        detail={"from": old, "to": node.name},
    )
    db.commit()
    db.refresh(node)
    return node


def move_node(
    db: Session,
    user: User,
    node: Node,
    *,
    parent_id: Optional[int],
    sort_order: int = 0,
) -> Node:
    if parent_id == node.id:
        raise ValueError("Cannot move a node under itself")
    if parent_id is not None:
        # prevent cycles
        current = db.get(Node, parent_id)
        while current is not None:
            if current.id == node.id:
                raise ValueError("Cannot move a node under its descendant")
            current = db.get(Node, current.parent_id) if current.parent_id else None
        if db.get(Node, parent_id) is None:
            raise ValueError("Parent not found")

    old_parent = node.parent_id
    node.parent_id = parent_id
    node.sort_order = sort_order
    record_audit(
        db,
        user=user,
        action="node.move",
        node=node,
        detail={"from_parent": old_parent, "to_parent": parent_id, "sort_order": sort_order},
    )
    db.commit()
    db.refresh(node)
    return node


def delete_node(db: Session, user: User, node: Node) -> None:
    node_id = node.id
    record_audit(
        db,
        user=user,
        action="node.delete",
        node=node,
        detail={"name": node.name, "kind": node.kind},
    )
    storage.delete_node_storage(node_id)
    db.delete(node)
    db.commit()


def search_nodes(db: Session, query: str) -> list[NodeOut]:
    q = f"%{query.strip()}%"
    nodes = (
        db.query(Node)
        .filter(Node.name.ilike(q))
        .order_by(Node.name.asc())
        .limit(50)
        .all()
    )
    return [node_to_out(db, n) for n in nodes]
