"""SQLAlchemy ORM models for Event-Sourced Versioned Knowledge Base.

Three tables implementing the immutable versioning pattern:
- kb_versions: Version metadata with active flag and SHA-256 checksum
- kb_modules: JSON snapshots of individual modules per version
- kb_audit_log: Append-only audit trail for all KB operations
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class KBVersion(Base):
    """Immutable version record. Each KB snapshot creates a new row.

    Only one version can be active at a time (is_active=True).
    Rollback = deactivate current, activate target. No deletes.
    """

    __tablename__ = "kb_versions"

    version_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    version_number = Column(Integer, nullable=False)
    version_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    checksum = Column(String(64), nullable=False)
    parent_version_id = Column(
        Uuid,
        ForeignKey("kb_versions.version_id"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    metadata_ = Column("metadata", JSON, default=dict)

    modules = relationship(
        "KBModule", back_populates="version", cascade="all, delete-orphan"
    )
    parent = relationship("KBVersion", remote_side=[version_id])

    __table_args__ = (
        Index("ix_kb_versions_is_active", "is_active"),
        Index("ix_kb_versions_created_at", "created_at"),
    )


class KBModule(Base):
    """JSON snapshot of a single module within a KB version.

    Each version can have multiple modules (core_engine, consumibles_margin, etc.).
    Module data is stored as JSON for flexible schema evolution.
    """

    __tablename__ = "kb_modules"

    module_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    version_id = Column(
        Uuid,
        ForeignKey("kb_versions.version_id"),
        nullable=False,
    )
    module_name = Column(String(100), nullable=False)
    module_data = Column(JSON, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    version = relationship("KBVersion", back_populates="modules")

    __table_args__ = (
        UniqueConstraint("version_id", "module_name", name="uq_version_module"),
        Index("ix_kb_modules_version_id", "version_id"),
        Index("ix_kb_modules_module_name", "module_name"),
    )


class KBAuditLog(Base):
    """Append-only audit trail for all KB operations.

    Records every action: version creation, activation, deactivation,
    rollback, read operations with context. Never deleted.
    """

    __tablename__ = "kb_audit_log"

    log_id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    action = Column(String(50), nullable=False)
    actor = Column(String(255), nullable=False)
    target_version_id = Column(Uuid, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_kb_audit_log_timestamp", "timestamp"),
        Index("ix_kb_audit_log_action", "action"),
        Index("ix_kb_audit_log_actor", "actor"),
    )
