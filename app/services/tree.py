from __future__ import annotations

import sqlite3
from typing import Optional

from app import repo
from app.models import Node, User
from app.schemas import NodeOut, TreeNodeOut
from app.services import storage
from app.services.audit import record_audit
from app.services.versions import create_empty_version, get_current_version


def node_to_out(db: sqlite3.Connection, node: Node) -> NodeOut:
    current = get_current_version(db, node.id)
    count = repo.count_versions(db, node.id)
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


def build_tree(db: sqlite3.Connection, parent_id: Optional[int] = None) -> list[TreeNodeOut]:
    nodes = repo.list_children(db, parent_id)
    result: list[TreeNodeOut] = []
    for node in nodes:
        base = node_to_out(db, node)
        result.append(
            TreeNodeOut(**base.model_dump(), children=build_tree(db, node.id))
        )
    return result


def create_node(
    db: sqlite3.Connection,
    user: User,
    *,
    name: str,
    kind: str,
    parent_id: Optional[int] = None,
) -> Node:
    if parent_id is not None:
        parent = repo.get_node(db, parent_id)
        if parent is None:
            raise ValueError("Parent node not found")

    siblings = repo.count_children(db, parent_id)
    node = repo.insert_node(
        db,
        parent_id=parent_id,
        name=name.strip(),
        kind=kind,
        created_by=user.id,
        sort_order=siblings,
    )

    create_empty_version(db, node, user)

    record_audit(
        db,
        user=user,
        action="node.create",
        node=node,
        detail={"kind": kind, "name": name},
    )
    db.commit()
    refreshed = repo.get_node(db, node.id)
    return refreshed or node


def rename_node(db: sqlite3.Connection, user: User, node: Node, name: str) -> Node:
    old = node.name
    new_name = name.strip()
    repo.update_node_name(db, node.id, new_name)
    node = repo.get_node(db, node.id) or node
    record_audit(
        db,
        user=user,
        action="node.rename",
        node=node,
        detail={"from": old, "to": node.name},
    )
    db.commit()
    return repo.get_node(db, node.id) or node


def move_node(
    db: sqlite3.Connection,
    user: User,
    node: Node,
    *,
    parent_id: Optional[int],
    sort_order: int = 0,
) -> Node:
    if parent_id == node.id:
        raise ValueError("Cannot move a node under itself")
    if parent_id is not None:
        current = repo.get_node(db, parent_id)
        while current is not None:
            if current.id == node.id:
                raise ValueError("Cannot move a node under its descendant")
            current = repo.get_node(db, current.parent_id) if current.parent_id else None
        if repo.get_node(db, parent_id) is None:
            raise ValueError("Parent not found")

    old_parent = node.parent_id
    repo.update_node_placement(db, node.id, parent_id=parent_id, sort_order=sort_order)
    node = repo.get_node(db, node.id) or node
    record_audit(
        db,
        user=user,
        action="node.move",
        node=node,
        detail={"from_parent": old_parent, "to_parent": parent_id, "sort_order": sort_order},
    )
    db.commit()
    return repo.get_node(db, node.id) or node


def delete_node(db: sqlite3.Connection, user: User, node: Node) -> None:
    node_id = node.id
    record_audit(
        db,
        user=user,
        action="node.delete",
        node=node,
        detail={"name": node.name, "kind": node.kind},
    )
    storage.delete_node_storage(node_id)
    repo.delete_node(db, node_id)
    db.commit()


def search_nodes(db: sqlite3.Connection, query: str) -> list[NodeOut]:
    nodes = repo.search_nodes(db, query)
    return [node_to_out(db, n) for n in nodes]
