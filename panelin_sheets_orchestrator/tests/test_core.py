"""Core unit tests for models, settings, idempotency, and FastAPI endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from panelin_sheets_orchestrator.models import (
    FillRequest,
    FillResponse,
    QueueProcessRequest,
    QueueProcessResponse,
    WriteEntry,
    WritePlan,
)


class TestModels:
    def test_fill_request_defaults(self):
        req = FillRequest(
            job_id="j1", template_id="tpl", spreadsheet_id="sid"
        )
        assert req.dry_run is False
        assert req.payload == {}

    def test_write_entry_serialization(self):
        entry = WriteEntry(range="A1", values=[["hello"]])
        d = entry.model_dump()
        assert d["range"] == "A1"
        assert d["values"] == [["hello"]]

    def test_write_plan_validation(self):
        plan = WritePlan(
            job_id="j1",
            version="1",
            writes=[WriteEntry(range="A1", values=[["v"]])],
            computed={},
            notes="ok",
        )
        assert len(plan.writes) == 1

    def test_fill_response(self):
        resp = FillResponse(
            job_id="j1", status="DONE", applied=True, total_updated_cells=5
        )
        assert resp.total_updated_cells == 5

    def test_queue_process_request_bounds(self):
        with pytest.raises(Exception):
            QueueProcessRequest(limit=0)
        with pytest.raises(Exception):
            QueueProcessRequest(limit=200)
        valid = QueueProcessRequest(limit=50)
        assert valid.limit == 50


class TestMemoryIdempotency:
    def test_lifecycle(self):
        from panelin_sheets_orchestrator.service import MemoryIdempotencyStore

        store = MemoryIdempotencyStore()
        assert store.get_done("j1") is None

        store.start("j1", "hash1")
        assert store.get_done("j1") is None

        store.done("j1", {"total_updated_cells": 3})
        result = store.get_done("j1")
        assert result is not None
        assert result["total_updated_cells"] == 3

    def test_fail(self):
        from panelin_sheets_orchestrator.service import MemoryIdempotencyStore

        store = MemoryIdempotencyStore()
        store.start("j2", "hash2")
        store.fail("j2", "boom")
        assert store.get_done("j2") is None


class TestPayloadHash:
    def test_deterministic(self):
        from panelin_sheets_orchestrator.service import payload_hash

        h1 = payload_hash({"a": 1, "b": 2})
        h2 = payload_hash({"b": 2, "a": 1})
        assert h1 == h2


class TestHealthEndpoint:
    def test_healthz(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True


class TestAuthEndpoint:
    def test_fill_no_key(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.post("/v1/fill", json={
            "job_id": "x",
            "template_id": "tpl",
            "spreadsheet_id": "sid",
        })
        assert resp.status_code == 401

    def test_fill_wrong_key(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.post(
            "/v1/fill",
            json={
                "job_id": "x",
                "template_id": "tpl",
                "spreadsheet_id": "sid",
            },
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401
