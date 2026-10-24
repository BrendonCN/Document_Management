from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["admin", "editor", "viewer"]
NodeKind = Literal["folder", "docx", "xlsx", "md", "txt", "pdf", "object"]
ViewMode = Literal["normal", "split", "md_render"]


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: Role
    last_login_at: Optional[datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    role: Role = "viewer"


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    username: str
    role: Optional[Role] = None
    display_name: Optional[str] = None
    create_if_missing: bool = False


class NodeCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=255)
    kind: NodeKind = "folder"


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class NodeMove(BaseModel):
    parent_id: Optional[int] = None
    sort_order: int = 0


class VersionOut(BaseModel):
    id: int
    node_id: int
    version_label: str
    version_date: datetime
    created_by: Optional[int] = None
    created_at: datetime
    ordinal: int
    filename: str
    content_type: Optional[str] = None

    model_config = {"from_attributes": True}


class VersionCreate(BaseModel):
    version_label: Optional[str] = None
    copy_from_version_id: Optional[int] = None


class VersionMetaUpdate(BaseModel):
    version_label: Optional[str] = None
    version_date: Optional[datetime] = None


class ContentSave(BaseModel):
    content: str
    create_new_version: bool = False
    version_label: Optional[str] = None


class SpreadsheetSave(BaseModel):
    sheets: dict[str, list[list[Any]]]
    create_new_version: bool = False
    version_label: Optional[str] = None


class NodeOut(BaseModel):
    id: int
    parent_id: Optional[int] = None
    name: str
    kind: NodeKind
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    sort_order: int
    current_version_id: Optional[int] = None
    version_count: int = 0

    model_config = {"from_attributes": True}


class TreeNodeOut(NodeOut):
    children: list[TreeNodeOut] = []


class AuditOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: str
    action: str
    node_id: Optional[int] = None
    path_snapshot: str
    detail_json: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DiffRequest(BaseModel):
    left_version_id: int
    right_version_id: int


class DiffApply(BaseModel):
    left_version_id: int
    right_version_id: int
    line_index: int
    direction: Literal["to_right", "to_left"]


class Message(BaseModel):
    ok: bool = True
    message: str = ""
    data: Optional[Any] = None
