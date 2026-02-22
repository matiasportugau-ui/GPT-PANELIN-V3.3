"""Core business logic for event-sourced KB versioning.

All state mutations happen here. The service layer encapsulates:
- Version creation with SHA-256 checksums
- Active version switching (atomic within a single transaction)
- Rollback mechanics
- Audit log recording
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .kb_models import KBAuditLog, KBModule, KBVersion
from .kb_schemas import CreateVersionRequest, RollbackRequest


def compute_module_checksum(module_data: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of sorted JSON module data."""
    canonical = json.dumps(
        module_data, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_version_checksum(module_checksums: List[str]) -> str:
    """SHA-256 of concatenated sorted module checksums."""
    combined = "|".join(sorted(module_checksums))
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


async def get_next_version_number(session: AsyncSession) -> int:
    """Get the next monotonically increasing version number."""
    result = await session.execute(
        select(func.coalesce(func.max(KBVersion.version_number), 0))
    )
    return result.scalar_one() + 1


async def create_version(
    session: AsyncSession,
    request: CreateVersionRequest,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> KBVersion:
    """Create a new immutable KB version with all modules.

    Steps:
    1. Compute SHA-256 checksum per module
    2. Compute aggregate version checksum
    3. Deactivate current active version (if any)
    4. Insert new version + modules in a single transaction
    5. Record audit log entry
    """
    # Compute checksums
    module_checksums = []
    module_objects = []
    for mod in request.modules:
        mod_checksum = compute_module_checksum(mod.module_data)
        module_checksums.append(mod_checksum)
        module_objects.append(
            KBModule(
                module_name=mod.module_name,
                module_data=mod.module_data,
                checksum=mod_checksum,
            )
        )

    version_checksum = compute_version_checksum(module_checksums)
    version_number = await get_next_version_number(session)

    # Deactivate current active version
    await session.execute(
        update(KBVersion)
        .where(KBVersion.is_active.is_(True))
        .values(is_active=False)
    )

    # Create new version
    version = KBVersion(
        version_number=version_number,
        version_type=request.version_type,
        description=request.description,
        author=request.author,
        is_active=True,
        checksum=version_checksum,
        parent_version_id=request.parent_version_id,
        metadata_=request.metadata,
    )

    # Attach modules
    for mod_obj in module_objects:
        mod_obj.version = version
    version.modules = module_objects

    session.add(version)

    # Record audit
    await record_audit(
        session=session,
        action="version_created",
        actor=request.author,
        target_version_id=version.version_id,
        details={
            "version_number": version_number,
            "version_type": request.version_type,
            "module_count": len(module_objects),
            "checksum": version_checksum,
        },
        ip_address=actor_ip,
        user_agent=user_agent,
    )

    return version


async def get_active_version(session: AsyncSession) -> Optional[KBVersion]:
    """Return the currently active KB version with all modules."""
    result = await session.execute(
        select(KBVersion)
        .where(KBVersion.is_active.is_(True))
        .options(selectinload(KBVersion.modules))
    )
    return result.scalar_one_or_none()


async def get_version_by_id(
    session: AsyncSession, version_id: UUID
) -> Optional[KBVersion]:
    """Return a specific version by ID with all modules."""
    result = await session.execute(
        select(KBVersion)
        .where(KBVersion.version_id == version_id)
        .options(selectinload(KBVersion.modules))
    )
    return result.scalar_one_or_none()


async def list_versions(
    session: AsyncSession, limit: int = 20, offset: int = 0
) -> List[KBVersion]:
    """Return all versions ordered by creation date (newest first)."""
    result = await session.execute(
        select(KBVersion)
        .order_by(KBVersion.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def count_versions(session: AsyncSession) -> int:
    """Return total number of versions."""
    result = await session.execute(select(func.count(KBVersion.version_id)))
    return result.scalar_one()


async def rollback_version(
    session: AsyncSession,
    request: RollbackRequest,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> KBVersion:
    """Rollback by switching active version pointer.

    Steps:
    1. Verify target version exists
    2. Deactivate current active version
    3. Activate target version
    4. Record audit log entry with rollback context

    Raises:
        ValueError: If target version does not exist
    """
    # Load target version
    target = await get_version_by_id(session, request.target_version_id)
    if target is None:
        raise ValueError(f"Version {request.target_version_id} not found")

    # Get current active for audit context
    current_active = await get_active_version(session)
    previous_version_id = (
        current_active.version_id if current_active else None
    )

    # Deactivate all active versions
    await session.execute(
        update(KBVersion)
        .where(KBVersion.is_active.is_(True))
        .values(is_active=False)
    )

    # Activate target
    await session.execute(
        update(KBVersion)
        .where(KBVersion.version_id == request.target_version_id)
        .values(is_active=True)
    )

    # Refresh target to get updated state
    target.is_active = True

    # Record audit
    await record_audit(
        session=session,
        action="rollback",
        actor=request.author,
        target_version_id=request.target_version_id,
        details={
            "reason": request.reason,
            "previous_version_id": str(previous_version_id) if previous_version_id else None,
            "target_version_number": target.version_number,
        },
        ip_address=actor_ip,
        user_agent=user_agent,
    )

    return target


async def get_audit_log(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    action_filter: Optional[str] = None,
) -> List[KBAuditLog]:
    """Query audit log entries."""
    query = select(KBAuditLog).order_by(KBAuditLog.timestamp.desc())
    if action_filter:
        query = query.where(KBAuditLog.action == action_filter)
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return list(result.scalars().all())


async def count_audit_entries(
    session: AsyncSession, action_filter: Optional[str] = None
) -> int:
    """Count audit log entries."""
    query = select(func.count(KBAuditLog.log_id))
    if action_filter:
        query = query.where(KBAuditLog.action == action_filter)
    result = await session.execute(query)
    return result.scalar_one()


async def record_audit(
    session: AsyncSession,
    action: str,
    actor: str,
    target_version_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> KBAuditLog:
    """Append an audit log entry (never deleted)."""
    entry = KBAuditLog(
        action=action,
        actor=actor,
        target_version_id=target_version_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(entry)
    return entry
