"""Integration tests for the Agno deterministic quotation workflow."""

from __future__ import annotations

from src.agent.workflow import build_panelin_workflow
from src.core.config import AppSettings


def _test_settings() -> AppSettings:
    return AppSettings(
        enable_llm_response_step=False,
        panelin_enable_mcp_tools=False,
        panelin_enable_memory_v2=False,
        panelin_enable_knowledge=False,
        panelin_enable_authorization=False,
        panelin_enable_tracing=False,
        panelin_enable_telemetry=False,
        database_url=None,
        db_host=None,
        db_connection_name=None,
    )


def test_workflow_runs_full_pipeline_for_system_quote():
    workflow = build_panelin_workflow(settings=_test_settings())
    result = workflow.run(
        input={
            "text": "Isodec EPS 100 mm / 10 paneles de 5 mts / techo completo a metal + flete",
            "mode": "pre_cotizacion",
            "client_name": "Cliente Test",
            "client_phone": "099123456",
            "client_location": "Montevideo",
        }
    )
    payload = result.content

    assert isinstance(payload, dict)
    assert payload["quotation"]["bom"]["panel_count"] > 0
    assert payload["quotation"]["pricing"]["subtotal_total_usd"] >= 0
    assert payload["sai"]["score"] >= 0
    assert "assistant_response" in payload


def test_workflow_skips_bom_for_accessories_only():
    workflow = build_panelin_workflow(settings=_test_settings())
    result = workflow.run(
        input={
            "text": "Necesito goteros frontales, goteros laterales, silicona y cinta butilo",
            "mode": "pre_cotizacion",
        }
    )
    payload = result.content

    assert isinstance(payload, dict)
    assert payload["bom_route"] == "skipped"
    assert payload["quotation"]["bom"]["panel_count"] == 0
    assert payload["quotation"]["request"]["familia"] is None
