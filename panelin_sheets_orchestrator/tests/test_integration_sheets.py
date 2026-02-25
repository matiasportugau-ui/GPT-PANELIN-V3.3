"""Integration-level tests (mocked Google Sheets + OpenAI)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from panelin_sheets_orchestrator.service import app, IDEM_STORE, MemoryIdempotencyStore


@pytest.fixture(autouse=True)
def _fresh_idempotency():
    """Replace the global idempotency store with a fresh in-memory instance."""
    import panelin_sheets_orchestrator.service as svc
    original = svc.IDEM_STORE
    svc.IDEM_STORE = MemoryIdempotencyStore()
    yield
    svc.IDEM_STORE = original


@pytest.fixture()
def client():
    return TestClient(app)


MOCK_WRITE_PLAN_JSON = json.dumps({
    "job_id": "test-job-1",
    "version": "1",
    "writes": [
        {"range": "EPS_100!B6", "values": [["Cliente Test"]]},
        {"range": "EPS_100!F3", "values": [["2026-02-25"]]},
    ],
    "computed": {},
    "notes": "Plan generado correctamente.",
})


class TestFillDryRun:
    @patch("panelin_sheets_orchestrator.service.sheets_batch_get")
    @patch("panelin_sheets_orchestrator.service.OpenAI")
    def test_dry_run_returns_plan(self, mock_openai_cls, mock_batch_get, client):
        mock_batch_get.return_value = {"valueRanges": []}

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "sk-test", "PANELIN_ORCH_API_KEY": "test-key-123"},
        ):
            import panelin_sheets_orchestrator.service as svc
            svc.SETTINGS = svc.load_settings()

            resp = client.post(
                "/v1/fill",
                json={
                    "job_id": "test-job-1",
                    "template_id": "cotizacion_isodec_eps_v1",
                    "spreadsheet_id": "FAKE_SID",
                    "payload": {"cliente": "Test"},
                    "dry_run": True,
                },
                headers={"X-API-Key": "test-key-123"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DRY_RUN"
        assert data["applied"] is False
        assert data["write_plan"] is not None
        assert len(data["write_plan"]["writes"]) == 2


class TestFillApply:
    @patch("panelin_sheets_orchestrator.service.sheets_batch_update")
    @patch("panelin_sheets_orchestrator.service.sheets_batch_get")
    @patch("panelin_sheets_orchestrator.service.OpenAI")
    def test_apply_writes_to_sheet(self, mock_openai_cls, mock_batch_get, mock_batch_update, client):
        mock_batch_get.return_value = {"valueRanges": []}
        mock_batch_update.return_value = {"totalUpdatedCells": 2}

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "sk-test", "PANELIN_ORCH_API_KEY": "test-key-123"},
        ):
            import panelin_sheets_orchestrator.service as svc
            svc.SETTINGS = svc.load_settings()

            resp = client.post(
                "/v1/fill",
                json={
                    "job_id": "test-job-apply",
                    "template_id": "cotizacion_isodec_eps_v1",
                    "spreadsheet_id": "FAKE_SID",
                    "payload": {"cliente": "Aplicar"},
                    "dry_run": False,
                },
                headers={"X-API-Key": "test-key-123"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "DONE"
        assert data["applied"] is True
        assert data["total_updated_cells"] == 2
        mock_batch_update.assert_called_once()


class TestIdempotency:
    @patch("panelin_sheets_orchestrator.service.sheets_batch_update")
    @patch("panelin_sheets_orchestrator.service.sheets_batch_get")
    @patch("panelin_sheets_orchestrator.service.OpenAI")
    def test_duplicate_job_returns_cached(self, mock_openai_cls, mock_batch_get, mock_batch_update, client):
        mock_batch_get.return_value = {"valueRanges": []}
        mock_batch_update.return_value = {"totalUpdatedCells": 1}

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_resp
        mock_openai_cls.return_value = mock_client

        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "sk-test", "PANELIN_ORCH_API_KEY": "test-key-123"},
        ):
            import panelin_sheets_orchestrator.service as svc
            svc.SETTINGS = svc.load_settings()

            headers = {"X-API-Key": "test-key-123"}
            body = {
                "job_id": "test-job-1",
                "template_id": "cotizacion_isodec_eps_v1",
                "spreadsheet_id": "FAKE_SID",
                "payload": {"cliente": "Test"},
                "dry_run": False,
            }

            resp1 = client.post("/v1/fill", json=body, headers=headers)
            assert resp1.status_code == 200
            assert resp1.json()["applied"] is True

            resp2 = client.post("/v1/fill", json=body, headers=headers)
            assert resp2.status_code == 200
            assert resp2.json()["applied"] is False
            assert "Idempotencia" in resp2.json()["notes"]
