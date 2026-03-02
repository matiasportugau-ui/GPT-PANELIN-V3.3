"""Core unit tests for models, settings, idempotency, and FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from panelin_sheets_orchestrator.models import (
    FillRequest,
    FillResponse,
    JobStatusResponse,
    QueueProcessRequest,
    QueueProcessResponse,
    ReadRequest,
    TemplateInfo,
    TemplateListResponse,
    ValidateRequest,
    ValidateResponse,
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

    def test_fill_response_with_validation(self):
        resp = FillResponse(
            job_id="j1",
            status="DONE",
            applied=True,
            total_updated_cells=5,
            validation={"warnings": ["test"]},
        )
        assert resp.total_updated_cells == 5
        assert resp.validation is not None

    def test_queue_process_request_bounds(self):
        with pytest.raises(Exception):
            QueueProcessRequest(limit=0)
        with pytest.raises(Exception):
            QueueProcessRequest(limit=200)
        valid = QueueProcessRequest(limit=50)
        assert valid.limit == 50

    def test_validate_request(self):
        req = ValidateRequest(
            product_family="ISODEC_EPS",
            thickness_mm=100,
            length_m=6.0,
            width_m=10.0,
        )
        assert req.usage == "techo"
        assert req.structure == "metal"
        assert req.safety_margin == 0.15

    def test_read_request(self):
        req = ReadRequest(spreadsheet_id="sid", ranges=["A1:B10"])
        assert len(req.ranges) == 1

    def test_template_info(self):
        t = TemplateInfo(
            template_id="tpl",
            sheet_name="Sheet1",
            writes_allowlist=["A1"],
            read_ranges=["A1:Z100"],
        )
        assert t.template_id == "tpl"

    def test_job_status_response(self):
        j = JobStatusResponse(job_id="j1", status="DONE", total_updated_cells=5)
        assert j.error is None


class TestMemoryIdempotency:
    def test_lifecycle(self):
        from panelin_sheets_orchestrator.service import MemoryIdempotencyStore

        store = MemoryIdempotencyStore()
        assert store.get_done("j1") is None
        assert store.get("j1") is None

        store.start("j1", "hash1")
        assert store.get("j1") is not None
        assert store.get("j1")["status"] == "RUNNING"
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
        record = store.get("j2")
        assert record["status"] == "ERROR"
        assert record["error"] == "boom"

    def test_idempotent_start(self):
        from panelin_sheets_orchestrator.service import MemoryIdempotencyStore

        store = MemoryIdempotencyStore()
        store.start("j3", "hash_a")
        store.start("j3", "hash_b")
        assert store.get("j3")["payload_hash"] == "hash_a"


class TestPayloadHash:
    def test_deterministic(self):
        from panelin_sheets_orchestrator.service import payload_hash

        h1 = payload_hash({"a": 1, "b": 2})
        h2 = payload_hash({"b": 2, "a": 1})
        assert h1 == h2

    def test_different_payloads(self):
        from panelin_sheets_orchestrator.service import payload_hash

        h1 = payload_hash({"a": 1})
        h2 = payload_hash({"a": 2})
        assert h1 != h2


class TestHealthEndpoint:
    def test_healthz(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "version" in data


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

    def test_validate_no_key(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.post("/v1/validate", json={
            "product_family": "ISODEC_EPS",
            "thickness_mm": 100,
            "length_m": 5.0,
            "width_m": 10.0,
        })
        assert resp.status_code == 401

    def test_templates_no_key(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get("/v1/templates")
        assert resp.status_code == 401


class TestValidateEndpoint:
    def test_valid_bom(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.post(
            "/v1/validate",
            json={
                "product_family": "ISODEC_EPS",
                "thickness_mm": 100,
                "length_m": 5.0,
                "width_m": 10.0,
                "usage": "techo",
                "structure": "metal",
            },
            headers={"X-API-Key": "test-key-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["bom_summary"]["panels_needed"] > 0
        assert data["bom_summary"]["supports"] >= 2

    def test_invalid_span(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.post(
            "/v1/validate",
            json={
                "product_family": "ISODEC_EPS",
                "thickness_mm": 100,
                "length_m": 7.0,
                "width_m": 10.0,
            },
            headers={"X-API-Key": "test-key-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0


class TestTemplatesEndpoint:
    def test_list_templates(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get(
            "/v1/templates",
            headers={"X-API-Key": "test-key-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert any(
            t["template_id"] == "cotizacion_isodec_eps_v1"
            for t in data["templates"]
        )

    def test_get_template(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get(
            "/v1/templates/cotizacion_isodec_eps_v1",
            headers={"X-API-Key": "test-key-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["template_id"] == "cotizacion_isodec_eps_v1"
        assert len(data["writes_allowlist"]) > 0

    def test_get_missing_template(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get(
            "/v1/templates/nonexistent",
            headers={"X-API-Key": "test-key-123"},
        )
        assert resp.status_code == 400


class TestJobStatusEndpoint:
    def test_not_found(self):
        from panelin_sheets_orchestrator.service import app

        client = TestClient(app)
        resp = client.get(
            "/v1/jobs/nonexistent",
            headers={"X-API-Key": "test-key-123"},
        )
        assert resp.status_code == 404
