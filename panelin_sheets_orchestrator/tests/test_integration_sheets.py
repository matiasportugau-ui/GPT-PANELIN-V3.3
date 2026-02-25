"""Integration-level tests (mocked Google Sheets + OpenAI)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from panelin_sheets_orchestrator.service import (
    IDEM_STORE,
    MemoryIdempotencyStore,
    app,
)


@pytest.fixture(autouse=True)
def _fresh_idempotency():
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
    "computed": {
        "panels_needed": "9",
        "supports": "3",
        "area_m2": "60.0",
        "fixing_points": "35",
    },
    "notes": "Plan generado correctamente.",
})


class TestFillDryRun:
    @patch("panelin_sheets_orchestrator.service.get_sheets_client")
    @patch("panelin_sheets_orchestrator.openai_planner.OpenAI")
    def test_dry_run_returns_plan(self, mock_openai_cls, mock_get_sheets, client):
        mock_sheets = MagicMock()
        mock_sheets.batch_get.return_value = {"valueRanges": []}
        mock_get_sheets.return_value = mock_sheets

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_resp.usage = None
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
    @patch("panelin_sheets_orchestrator.service.get_sheets_client")
    @patch("panelin_sheets_orchestrator.openai_planner.OpenAI")
    def test_apply_writes_to_sheet(self, mock_openai_cls, mock_get_sheets, client):
        mock_sheets = MagicMock()
        mock_sheets.batch_get.return_value = {"valueRanges": []}
        mock_sheets.batch_update.return_value = {"totalUpdatedCells": 2}
        mock_get_sheets.return_value = mock_sheets

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_resp.usage = None
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
        mock_sheets.batch_update.assert_called_once()


class TestFillWithBOM:
    @patch("panelin_sheets_orchestrator.service.get_sheets_client")
    @patch("panelin_sheets_orchestrator.openai_planner.OpenAI")
    def test_fill_with_bom_data(self, mock_openai_cls, mock_get_sheets, client):
        """When payload includes product_family/thickness/length/width, BOM is precomputed."""
        mock_sheets = MagicMock()
        mock_sheets.batch_get.return_value = {"valueRanges": []}
        mock_get_sheets.return_value = mock_sheets

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_resp.usage = None
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
                    "job_id": "test-bom-fill",
                    "template_id": "cotizacion_isodec_eps_v1",
                    "spreadsheet_id": "FAKE_SID",
                    "payload": {
                        "cliente": "BOM Test",
                        "product_family": "ISODEC_EPS",
                        "thickness_mm": 100,
                        "length_m": 5.0,
                        "width_m": 10.0,
                        "usage": "techo",
                        "structure": "metal",
                    },
                    "dry_run": True,
                },
                headers={"X-API-Key": "test-key-123"},
            )

        assert resp.status_code == 200
        call_args = mock_client.responses.create.call_args
        user_content = json.loads(call_args.kwargs["input"][1]["content"])
        assert "bom_precomputed" in user_content


class TestFillRejectsFormulas:
    @patch("panelin_sheets_orchestrator.service.get_sheets_client")
    @patch("panelin_sheets_orchestrator.openai_planner.OpenAI")
    def test_formula_in_plan_rejected(self, mock_openai_cls, mock_get_sheets, client):
        mock_sheets = MagicMock()
        mock_sheets.batch_get.return_value = {"valueRanges": []}
        mock_get_sheets.return_value = mock_sheets

        bad_plan = json.dumps({
            "job_id": "test-formula",
            "version": "1",
            "writes": [
                {"range": "EPS_100!B6", "values": [["=SUM(A1:A10)"]]},
            ],
            "computed": {"panels_needed": "0", "supports": "0", "area_m2": "0", "fixing_points": "0"},
            "notes": "",
        })
        mock_resp = MagicMock()
        mock_resp.output_text = bad_plan
        mock_resp.usage = None
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
                    "job_id": "test-formula",
                    "template_id": "cotizacion_isodec_eps_v1",
                    "spreadsheet_id": "FAKE_SID",
                    "payload": {},
                    "dry_run": False,
                },
                headers={"X-API-Key": "test-key-123"},
            )

        assert resp.status_code == 400
        assert "fórmula" in resp.json()["detail"].lower()


class TestIdempotency:
    @patch("panelin_sheets_orchestrator.service.get_sheets_client")
    @patch("panelin_sheets_orchestrator.openai_planner.OpenAI")
    def test_duplicate_job_returns_cached(self, mock_openai_cls, mock_get_sheets, client):
        mock_sheets = MagicMock()
        mock_sheets.batch_get.return_value = {"valueRanges": []}
        mock_sheets.batch_update.return_value = {"totalUpdatedCells": 1}
        mock_get_sheets.return_value = mock_sheets

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_resp.usage = None
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

    @patch("panelin_sheets_orchestrator.service.get_sheets_client")
    @patch("panelin_sheets_orchestrator.openai_planner.OpenAI")
    def test_job_status_after_fill(self, mock_openai_cls, mock_get_sheets, client):
        mock_sheets = MagicMock()
        mock_sheets.batch_get.return_value = {"valueRanges": []}
        mock_sheets.batch_update.return_value = {"totalUpdatedCells": 2}
        mock_get_sheets.return_value = mock_sheets

        mock_resp = MagicMock()
        mock_resp.output_text = MOCK_WRITE_PLAN_JSON
        mock_resp.usage = None
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
            client.post(
                "/v1/fill",
                json={
                    "job_id": "status-check-job",
                    "template_id": "cotizacion_isodec_eps_v1",
                    "spreadsheet_id": "FAKE_SID",
                    "payload": {},
                    "dry_run": False,
                },
                headers=headers,
            )

            resp = client.get(
                "/v1/jobs/status-check-job",
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "DONE"
            assert resp.json()["total_updated_cells"] == 2
