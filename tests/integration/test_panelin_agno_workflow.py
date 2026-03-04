"""Integration tests for the Agno deterministic workflow migration."""

from __future__ import annotations

from src.agent.workflow import build_panelin_workflow, run_panelin_workflow
from src.core.config import Settings


def _test_settings() -> Settings:
    return Settings(
        enable_llm_response=False,
        enable_mcp_tools=False,
        openai_api_key=None,
        anthropic_api_key=None,
    )


def test_workflow_generates_structured_quote():
    workflow = build_panelin_workflow(_test_settings(), db=None)
    result = run_panelin_workflow(
        workflow,
        text="Isodec EPS 100 mm / techo 7 x 10 / estructura metal",
        mode="pre_cotizacion",
    )

    assert result["quote"]["quote_id"].startswith("PV4-")
    assert result["quote"]["mode"] == "pre_cotizacion"
    assert "pricing" in result["quote"]
    assert "sai" in result
    assert isinstance(result["response_text"], str)


def test_workflow_skips_bom_for_accessories_only():
    workflow = build_panelin_workflow(_test_settings(), db=None)
    result = run_panelin_workflow(
        workflow,
        text="Necesito 12 tornillos, 24 arandelas y 4 selladores para reposición (solo accesorios)",
        mode="pre_cotizacion",
    )

    quote = result["quote"]
    assert quote["classification"]["request_type"] == "accessories_only"
    assert quote["bom"]["system_key"] == "accessories_only"
    assert quote["pricing"]["subtotal_total_usd"] == 0.0


def test_workflow_reuses_session_id_when_provided():
    workflow = build_panelin_workflow(_test_settings(), db=None)
    session_id = "session-panelin-test"
    first = run_panelin_workflow(
        workflow,
        text="Isopanel EPS 50 mm / pared 20 x 3",
        session_id=session_id,
    )
    second = run_panelin_workflow(
        workflow,
        text="Actualizar cotización: agregar 2 paneles",
        session_id=session_id,
    )

    assert first["session_id"] == session_id
    assert second["session_id"] == session_id
    assert first["run_id"] != second["run_id"]

