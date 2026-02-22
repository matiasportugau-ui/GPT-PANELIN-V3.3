"""Pydantic schemas for KB Architecture request validation and response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ModuleInput(BaseModel):
    """A single module within a KB version."""

    module_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Module identifier: core_engine, consumibles_margin, etc.",
    )
    module_data: Dict[str, Any] = Field(
        ..., description="JSONB module content"
    )


class CreateVersionRequest(BaseModel):
    """POST /api/kb/architecture - Create a new KB version."""

    version_type: str = Field(
        default="full_snapshot",
        description="Type: full_snapshot, partial_update, architectural_update",
    )
    description: str = Field(..., min_length=5, max_length=1000)
    author: str = Field(..., min_length=1, max_length=255)
    modules: List[ModuleInput] = Field(..., min_length=1)
    password: str = Field(..., description="KB write password")
    parent_version_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("modules")
    @classmethod
    def validate_unique_module_names(cls, v: List[ModuleInput]) -> List[ModuleInput]:
        names = [m.module_name for m in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate module names are not allowed")
        return v


class RollbackRequest(BaseModel):
    """POST /api/kb/architecture/rollback - Rollback to a specific version."""

    target_version_id: UUID
    reason: str = Field(..., min_length=5, max_length=1000)
    author: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., description="KB write password")


class ModuleResponse(BaseModel):
    """Serialized KB module."""

    module_id: UUID
    module_name: str
    module_data: Dict[str, Any]
    checksum: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionResponse(BaseModel):
    """Serialized KB version with modules."""

    version_id: UUID
    version_number: int
    version_type: str
    description: str
    author: str
    is_active: bool
    checksum: str
    parent_version_id: Optional[UUID] = None
    created_at: datetime
    modules: List[ModuleResponse] = []

    model_config = {"from_attributes": True}


class VersionListItem(BaseModel):
    """Lightweight version info for list endpoint (no module data)."""

    version_id: UUID
    version_number: int
    version_type: str
    description: str
    author: str
    is_active: bool
    checksum: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogEntry(BaseModel):
    """Serialized audit log entry."""

    log_id: UUID
    action: str
    actor: str
    target_version_id: Optional[UUID] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}
