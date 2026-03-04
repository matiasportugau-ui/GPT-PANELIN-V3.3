"""Integration tests for Panelin Agno migration components."""

from __future__ import annotations

import os

from agno.db.in_memory import InMemoryDb


def _set_test_env() -> None:
    os.environ["PANELIN_ENABLE_LLM_RESPONSE"] = "false"
    os.environ["PANELIN_USE_IN_MEMORY_DB"] = "true"
    os.environ["PANELIN_ENABLE_MCP_TOOLS"] = "false"


def _get_step_output(result, step_name: str):
    for step in result.step_results:
        if step.step_name == step_name:
            return step
    raise AssertionError(f"Step '{step_name}' not found")


def test_workflow_runs_full_pipeline_for_roof_quote():
    _set_test_env()
    from src.core.config import get_settings

    get_settings.cache_clear()

    from src.agent.workflow import build_panelin_workflow
    from src.quotation.service import QuotationService

    workflow = build_panelin_workflow(
        settings=get_settings(),
        db=InMemoryDb(),
        service=QuotationService(),
    )
    result = workflow.run(
        {
            "text": "Isodec EPS 100 mm / 6 paneles de 6.5 mts / techo completo",
            "mode": "pre_cotizacion",
        }
    )

    assert result.status.value == "COMPLETED"
    assert "Total USD" in result.content

    router_step = _get_step_output(result, "route_bom_pricing")
    inner_names = [inner.step_name for inner in router_step.steps[0].steps]
    assert inner_names == ["calculate_bom", "calculate_pricing"]

    validation_step = _get_step_output(result, "validate_quote")
    output = validation_step.content["output"]
    assert output["pricing"]["subtotal_total_usd"] > 0
    assert output["bom"]["panel_count"] > 0


def test_workflow_routes_accessories_only_to_skip_path():
    _set_test_env()
    from src.core.config import get_settings

    get_settings.cache_clear()

    from src.agent.workflow import build_panelin_workflow
    from src.quotation.service import QuotationService

    workflow = build_panelin_workflow(
        settings=get_settings(),
        db=InMemoryDb(),
        service=QuotationService(),
    )
    result = workflow.run(
        {
            "text": "12 tornillos y 8 silicona",
            "mode": "pre_cotizacion",
        }
    )

    assert result.status.value == "COMPLETED"

    router_step = _get_step_output(result, "route_bom_pricing")
    inner_names = [inner.step_name for inner in router_step.steps[0].steps]
    assert inner_names == ["skip_bom_for_accessories", "skip_pricing_for_accessories"]


def test_agentos_exposes_agent_workflow_and_legacy_wolf_routes():
    _set_test_env()
    from src.core.config import get_settings

    get_settings.cache_clear()

    from src.app import create_agent_os

    agent_os = create_agent_os(get_settings())
    paths = {route.path for route in agent_os.get_routes() if hasattr(route, "path")}

    assert "/agents/{agent_id}/runs" in paths
    assert "/workflows/{workflow_id}/runs" in paths
    assert "/sessions" in paths

    # Wolf API compatibility routes
    assert "/calculate_quote" in paths
    assert "/find_products" in paths
    assert "/kb/conversations" in paths
    assert "/sheets/consultations" in paths
