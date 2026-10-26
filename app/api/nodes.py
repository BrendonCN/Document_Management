from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app import repo
from app.auth.deps import require_roles, require_user
from app.db import get_db
from app.models import User
from app.schemas import Message, NodeCreate, NodeMove, NodeOut, NodeUpdate, TreeNodeOut
from app.services import tree as tree_svc

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.get("/tree", response_model=list[TreeNodeOut])
def get_tree(
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    return tree_svc.build_tree(db)


@router.get("/search", response_model=list[NodeOut])
def search(
    q: str = Query(..., min_length=1),
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    return tree_svc.search_nodes(db, q)


@router.get("/{node_id}", response_model=NodeOut)
def get_node(
    node_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_user),
):
    node = repo.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return tree_svc.node_to_out(db, node)


@router.post("", response_model=NodeOut)
def create_node(
    payload: NodeCreate,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    try:
        node = tree_svc.create_node(
            db,
            user,
            name=payload.name,
            kind=payload.kind,
            parent_id=payload.parent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return tree_svc.node_to_out(db, node)


@router.patch("/{node_id}", response_model=NodeOut)
def update_node(
    node_id: int,
    payload: NodeUpdate,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    node = repo.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        if payload.name is not None:
            node = tree_svc.rename_node(db, user, node, payload.name)
        if payload.parent_id is not None or payload.sort_order is not None:
            node = tree_svc.move_node(
                db,
                user,
                node,
                parent_id=payload.parent_id if payload.parent_id is not None else node.parent_id,
                sort_order=payload.sort_order if payload.sort_order is not None else node.sort_order,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return tree_svc.node_to_out(db, node)


@router.post("/{node_id}/move", response_model=NodeOut)
def move_node(
    node_id: int,
    payload: NodeMove,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    node = repo.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    try:
        node = tree_svc.move_node(
            db, user, node, parent_id=payload.parent_id, sort_order=payload.sort_order
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return tree_svc.node_to_out(db, node)


@router.delete("/{node_id}", response_model=Message)
def delete_node(
    node_id: int,
    db: sqlite3.Connection = Depends(get_db),
    user: User = Depends(require_roles("admin", "editor")),
):
    node = repo.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    tree_svc.delete_node(db, user, node)
    return Message(message="Deleted")
