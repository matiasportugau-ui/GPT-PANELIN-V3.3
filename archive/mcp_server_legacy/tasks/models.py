"""Data models for background task tracking.

Defines the task lifecycle: pending -> running -> completed | failed | cancelled.
Each task carries its type, input arguments, progress, and result/error.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class TaskStatus(str, enum.Enum):
    """Lifecycle states for a background task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, enum.Enum):
    """Supported background task types."""

    BATCH_BOM = "batch_bom_calculate"
    BULK_PRICING = "bulk_price_check"
    FULL_QUOTATION = "full_quotation"


@dataclass
class TaskProgress:
    """Tracks incremental progress within a running task."""

    total_items: int = 0
    completed_items: int = 0
    current_item: str = ""

    @property
    def percentage(self) -> float:
        if self.total_items == 0:
            return 0.0
        return round((self.completed_items / self.total_items) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "current_item": self.current_item,
            "percentage": self.percentage,
        }


@dataclass
class Task:
    """Represents a single background task with full lifecycle tracking."""

    task_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    arguments: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: TaskProgress = field(default_factory=TaskProgress)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    started_at: str | None = None
    completed_at: str | None = None

    def mark_running(self) -> None:
        """Transition task to running state."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def mark_completed(self, result: dict[str, Any]) -> None:
        """Transition task to completed state with result."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def mark_failed(self, error: str) -> None:
        """Transition task to failed state with error message."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def mark_cancelled(self) -> None:
        """Transition task to cancelled state."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_summary(self) -> dict[str, Any]:
        """Return a lightweight summary (no result data)."""
        summary: dict[str, Any] = {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
        }
        if self.started_at:
            summary["started_at"] = self.started_at
        if self.completed_at:
            summary["completed_at"] = self.completed_at
        if self.status == TaskStatus.RUNNING:
            summary["progress"] = self.progress.to_dict()
        if self.error:
            summary["error"] = self.error
        return summary

    def to_full_dict(self) -> dict[str, Any]:
        """Return full task data including result."""
        data = self.to_summary()
        if self.result is not None:
            data["result"] = self.result
        if self.status == TaskStatus.RUNNING:
            data["progress"] = self.progress.to_dict()
        data["arguments"] = self.arguments
        return data
