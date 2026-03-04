from __future__ import annotations

from src.agent.workflow import build_panelin_workflow
from src.quotation.service import QuotationService


def _build_workflow():
    service = QuotationService()
    return build_panelin_workflow(service=service, response_agent=None, db=None)


def test_workflow_roof_path_runs_deterministic_pipeline():
    workflow = _build_workflow()
    result = workflow.run(
        input={
            "text": "Isodec EPS 100 mm / 6 paneles de 6.5 mts / techo completo a metal",
            "mode": "pre_cotizacion",
            "client_name": "Cliente Test",
        }
    )
    content = result.content

    assert isinstance(content, dict)
    assert "quotation" in content
    assert "sai" in content
    assert "message" in content
    assert content["quotation"]["classification"]["request_type"] in {"roof_system", "mixed"}
    assert content["quotation"]["pricing"]["subtotal_total_usd"] >= 0


def test_workflow_accessories_path_skips_bom_branch():
    workflow = _build_workflow()
    result = workflow.run(
        input={
            "text": "Necesito varilla, tuerca, tortuga pvc y silicona",
            "mode": "pre_cotizacion",
        }
    )
    content = result.content
    quotation = content["quotation"]

    assert quotation["classification"]["request_type"] == "accessories_only"
    assert quotation["bom"]["panel_count"] == 0
    assert any(
        "accessories" in note.lower()
        for note in quotation.get("processing_notes", []) + quotation.get("assumptions_used", [])
    ) or any(
        "accessories" in note.lower()
        for note in content.get("quotation", {}).get("processing_notes", [])
    )
