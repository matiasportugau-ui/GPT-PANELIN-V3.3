"""Tests for the audit logging module."""

from __future__ import annotations

import json

from panelin_sheets_orchestrator.audit import (
    AuditEvent,
    audit_fill_request,
    audit_fill_result,
    audit_openai_call,
    audit_queue_batch,
    audit_sheets_api_call,
    audit_validation_failure,
)


class TestAuditEvent:
    def test_basic_event(self):
        ev = AuditEvent("test.action", job_id="j1")
        d = ev.to_dict()
        assert d["action"] == "test.action"
        assert d["job_id"] == "j1"
        assert d["severity"] == "INFO"
        assert "elapsed_ms" in d

    def test_with_data(self):
        ev = AuditEvent("test.action").with_data(key1="val1", key2=42)
        d = ev.to_dict()
        assert d["data"]["key1"] == "val1"
        assert d["data"]["key2"] == 42

    def test_error_severity(self):
        ev = AuditEvent("test.fail")
        d = ev.to_dict(severity="error", error="boom")
        assert d["severity"] == "ERROR"
        assert d["error"] == "boom"

    def test_emit_returns_dict(self):
        ev = AuditEvent("test.emit", job_id="j2")
        result = ev.emit("info")
        assert isinstance(result, dict)
        assert result["action"] == "test.emit"

    def test_spreadsheet_and_template(self):
        ev = AuditEvent(
            "test.full",
            job_id="j3",
            spreadsheet_id="sid",
            template_id="tpl",
        )
        d = ev.to_dict()
        assert d["spreadsheet_id"] == "sid"
        assert d["template_id"] == "tpl"


class TestAuditHelpers:
    def test_fill_request(self):
        result = audit_fill_request(
            job_id="j1",
            template_id="tpl",
            spreadsheet_id="sid",
            dry_run=True,
            payload_keys=["cliente", "fecha"],
        )
        assert result["action"] == "fill.request"
        assert result["data"]["dry_run"] is True

    def test_fill_result(self):
        result = audit_fill_result(
            job_id="j1",
            status="DONE",
            writes_count=3,
            total_updated_cells=10,
        )
        assert result["data"]["status"] == "DONE"

    def test_validation_failure(self):
        result = audit_validation_failure(
            job_id="j1", rule="autoportancia", detail="span exceeded"
        )
        assert result["severity"] == "WARNING"

    def test_openai_call(self):
        result = audit_openai_call(
            job_id="j1",
            model="gpt-4o-mini",
            input_tokens=500,
            output_tokens=200,
            duration_ms=1234.5,
        )
        assert result["data"]["model"] == "gpt-4o-mini"

    def test_sheets_api_call(self):
        result = audit_sheets_api_call(
            job_id="j1",
            operation="batchUpdate",
            spreadsheet_id="sid",
            ranges_count=3,
            duration_ms=456.7,
        )
        assert result["data"]["operation"] == "batchUpdate"

    def test_queue_batch(self):
        result = audit_queue_batch(
            processed=10, succeeded=8, failed=2, duration_ms=5000.0
        )
        assert result["data"]["processed"] == 10
