"""
Structured audit logging for Panelin Sheets Orchestrator.

Emits JSON-line logs compatible with Google Cloud Logging's jsonPayload parsing.
Each audit event captures who/what/when/result for traceability and compliance.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger("panelin.sheets.audit")

# Cloud Logging severity mapping
_SEVERITY_MAP = {
    "debug": "DEBUG",
    "info": "INFO",
    "warning": "WARNING",
    "error": "ERROR",
    "critical": "CRITICAL",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditEvent:
    """Structured audit event builder."""

    def __init__(
        self,
        action: str,
        *,
        job_id: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> None:
        self.action = action
        self.job_id = job_id
        self.spreadsheet_id = spreadsheet_id
        self.template_id = template_id
        self.timestamp = _utc_now_iso()
        self.extras: Dict[str, Any] = {}
        self._start_time = time.monotonic()

    def with_data(self, **kwargs: Any) -> "AuditEvent":
        self.extras.update(kwargs)
        return self

    def _elapsed_ms(self) -> float:
        return round((time.monotonic() - self._start_time) * 1000, 2)

    def to_dict(self, severity: str = "info", error: Optional[str] = None) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "severity": _SEVERITY_MAP.get(severity, "INFO"),
            "message": f"audit.{self.action}",
            "timestamp": self.timestamp,
            "action": self.action,
            "elapsed_ms": self._elapsed_ms(),
        }
        if self.job_id:
            d["job_id"] = self.job_id
        if self.spreadsheet_id:
            d["spreadsheet_id"] = self.spreadsheet_id
        if self.template_id:
            d["template_id"] = self.template_id
        if error:
            d["error"] = error
        if self.extras:
            d["data"] = self.extras
        return d

    def emit(self, severity: str = "info", error: Optional[str] = None) -> Dict[str, Any]:
        """Emit the audit event as a structured JSON log line."""
        payload = self.to_dict(severity=severity, error=error)
        line = json.dumps(payload, ensure_ascii=False, default=str)
        log_fn = getattr(logger, severity, logger.info)
        log_fn(line)
        return payload


@contextmanager
def audit_span(
    action: str,
    *,
    job_id: Optional[str] = None,
    spreadsheet_id: Optional[str] = None,
    template_id: Optional[str] = None,
) -> Generator[AuditEvent, None, None]:
    """Context manager that emits start/end audit events with timing."""
    ev = AuditEvent(
        action,
        job_id=job_id,
        spreadsheet_id=spreadsheet_id,
        template_id=template_id,
    )
    ev.emit("info")
    try:
        yield ev
        ev.emit("info")
    except Exception as exc:
        ev.emit("error", error=str(exc))
        raise


def audit_fill_request(
    *,
    job_id: str,
    template_id: str,
    spreadsheet_id: str,
    dry_run: bool,
    payload_keys: list,
) -> Dict[str, Any]:
    return AuditEvent(
        "fill.request",
        job_id=job_id,
        spreadsheet_id=spreadsheet_id,
        template_id=template_id,
    ).with_data(
        dry_run=dry_run,
        payload_keys=payload_keys,
    ).emit("info")


def audit_fill_result(
    *,
    job_id: str,
    status: str,
    writes_count: int,
    total_updated_cells: int,
    notes: str = "",
) -> Dict[str, Any]:
    return AuditEvent(
        "fill.result",
        job_id=job_id,
    ).with_data(
        status=status,
        writes_count=writes_count,
        total_updated_cells=total_updated_cells,
        notes=notes,
    ).emit("info")


def audit_validation_failure(
    *,
    job_id: str,
    rule: str,
    detail: str,
) -> Dict[str, Any]:
    return AuditEvent(
        "validation.failure",
        job_id=job_id,
    ).with_data(
        rule=rule,
        detail=detail,
    ).emit("warning")


def audit_openai_call(
    *,
    job_id: str,
    model: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    return AuditEvent(
        "openai.call",
        job_id=job_id,
    ).with_data(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
    ).emit("info")


def audit_sheets_api_call(
    *,
    job_id: str,
    operation: str,
    spreadsheet_id: str,
    ranges_count: int,
    retries: int = 0,
    duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    return AuditEvent(
        "sheets.api_call",
        job_id=job_id,
        spreadsheet_id=spreadsheet_id,
    ).with_data(
        operation=operation,
        ranges_count=ranges_count,
        retries=retries,
        duration_ms=duration_ms,
    ).emit("info")


def audit_queue_batch(
    *,
    processed: int,
    succeeded: int,
    failed: int,
    duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    return AuditEvent(
        "queue.batch",
    ).with_data(
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        duration_ms=duration_ms,
    ).emit("info")
