"""FastAPI routes for Event-Sourced Versioned Knowledge Base.

Endpoints:
- POST /api/kb/architecture          Create new version with modules
- GET  /api/kb/architecture/active   Get active version
- GET  /api/kb/architecture/versions List all versions (paginated)
- GET  /api/kb/architecture/audit    Query audit log
- GET  /api/kb/architecture/{id}     Get specific version
- POST /api/kb/architecture/rollback Rollback to previous version
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .kb_auth import require_api_key, validate_write_password
from .kb_database import get_db_session
from .kb_schemas import (
    AuditLogEntry,
    CreateVersionRequest,
    RollbackRequest,
    VersionListItem,
    VersionResponse,
)
from .kb_service import (
    count_audit_entries,
    count_versions,
    create_version,
    get_active_version,
    get_audit_log,
    get_version_by_id,
    list_versions,
    rollback_version,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb/architecture", tags=["kb_architecture"])


@router.post("", status_code=201)
async def create_kb_version(
    request_body: CreateVersionRequest,
    request: Request,
    _: None = Depends(require_api_key),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Create a new immutable KB version with all modules.

    Requires: X-API-Key header + KB write password in body.
    """
    validate_write_password(request_body.password)
    try:
        version = await create_version(
            session=session,
            request=request_body,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await session.commit()
        return {
            "ok": True,
            "version": VersionResponse.model_validate(version).model_dump(
                mode="json"
            ),
        }
    except Exception:
        await session.rollback()
        logger.exception("Failed to create KB version")
        raise HTTPException(status_code=500, detail="Failed to create KB version")


@router.get("/active")
async def get_active_kb_version(
    _: None = Depends(require_api_key),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get the currently active KB version with all modules.

    Requires: X-API-Key header.
    """
    version = await get_active_version(session)
    if not version:
        raise HTTPException(status_code=404, detail="No active KB version found")
    return {
        "ok": True,
        "version": VersionResponse.model_validate(version).model_dump(
            mode="json"
        ),
    }


@router.get("/versions")
async def list_kb_versions(
    _: None = Depends(require_api_key),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """List all KB versions (paginated, newest first).

    Requires: X-API-Key header.
    """
    versions = await list_versions(session, limit=limit, offset=offset)
    total = await count_versions(session)
    return {
        "ok": True,
        "versions": [
            VersionListItem.model_validate(v).model_dump(mode="json")
            for v in versions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/audit")
async def query_audit_log(
    _: None = Depends(require_api_key),
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
) -> dict:
    """Query the KB audit log.

    Requires: X-API-Key header.
    """
    entries = await get_audit_log(
        session, limit=limit, offset=offset, action_filter=action
    )
    total = await count_audit_entries(session, action_filter=action)
    return {
        "ok": True,
        "entries": [
            AuditLogEntry.model_validate(e).model_dump(mode="json") for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{version_id}")
async def get_kb_version(
    version_id: UUID,
    _: None = Depends(require_api_key),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get a specific KB version by ID with all modules.

    Requires: X-API-Key header.
    """
    version = await get_version_by_id(session, version_id)
    if not version:
        raise HTTPException(
            status_code=404, detail=f"Version {version_id} not found"
        )
    return {
        "ok": True,
        "version": VersionResponse.model_validate(version).model_dump(
            mode="json"
        ),
    }


@router.post("/rollback")
async def rollback_kb_version(
    request_body: RollbackRequest,
    request: Request,
    _: None = Depends(require_api_key),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Rollback to a previous KB version.

    Does not delete any data. Switches the active pointer.
    Requires: X-API-Key header + KB write password in body.
    """
    validate_write_password(request_body.password)
    try:
        version = await rollback_version(
            session=session,
            request=request_body,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await session.commit()
        return {
            "ok": True,
            "version": VersionResponse.model_validate(version).model_dump(
                mode="json"
            ),
            "message": f"Rolled back to version {version.version_number}",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        await session.rollback()
        logger.exception("Failed to rollback KB version")
        raise HTTPException(status_code=500, detail="Failed to rollback KB version")
