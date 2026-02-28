"""Panelin API entrypoint compatible with Cloud Run."""

from __future__ import annotations

import os

from fastapi import APIRouter
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from panelin_v4.engine.classifier import OperatingMode, classify_request
from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.parser import parse_request
from panelin_v4.engine.pricing_engine import PricingResult, calculate_pricing
from panelin_v4.engine.quotation_engine import _apply_defaults, process_quotation
from panelin_v4.engine.sre_engine import calculate_sre
from panelin_v4.engine.validation_engine import validate_quotation
from panelin_v4.evaluator.sai_engine import calculate_sai
from wolf_api.main import app


class PanelinEngineInput(BaseModel):
    text: str = Field(..., min_length=1)
    mode: str = Field(default="pre_cotizacion")
    client_name: str | None = None
    client_phone: str | None = None
    client_location: str | None = None


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}

# Preserve legacy operation IDs used by existing API consumers.
LEGACY_OPERATION_IDS: dict[tuple[str, str], str] = {
    ("GET", "/sheets/stats"): "getSheetStats",
    ("GET", "/sheets/search"): "searchClients",
    ("GET", "/sheets/row/{row_number}"): "getRow",
    ("GET", "/sheets/consultations"): "readConsultations",
    ("POST", "/sheets/consultations"): "addConsultation",
    ("POST", "/sheets/quotation_line"): "addQuotationLine",
    ("PATCH", "/sheets/update_row"): "updateRow",
    ("POST", "/kb/conversations"): "persistConversation",
    ("POST", "/kb/customers"): "saveCustomer",
    ("POST", "/kb/corrections"): "registerCorrection",
}


def _set_legacy_operation_ids() -> None:
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            operation_id = LEGACY_OPERATION_IDS.get((method, route.path))
            if operation_id:
                route.operation_id = operation_id


def _resolve_mode(raw_mode: str | None) -> OperatingMode:
    mode_key = (raw_mode or "pre_cotizacion").strip().lower()
    if mode_key not in MODE_MAP:
        valid_modes = ", ".join(sorted(MODE_MAP.keys()))
        raise ValueError(f"Invalid mode '{raw_mode}'. Valid options: {valid_modes}")
    return MODE_MAP[mode_key]


def _run_quote(input_data: PanelinEngineInput) -> dict:
    mode = _resolve_mode(input_data.mode)
    output = process_quotation(
        text=input_data.text,
        force_mode=mode,
        client_name=input_data.client_name,
        client_phone=input_data.client_phone,
        client_location=input_data.client_location,
    )
    return output.to_dict()


def _run_validation(input_data: PanelinEngineInput) -> dict:
    forced_mode = _resolve_mode(input_data.mode)
    classification = classify_request(input_data.text, force_mode=forced_mode)
    mode = classification.operating_mode

    request = parse_request(input_data.text)

    if input_data.client_name:
        request.client.name = input_data.client_name
    if input_data.client_phone:
        request.client.phone = input_data.client_phone
    if input_data.client_location:
        request.client.location = input_data.client_location

    assumptions = _apply_defaults(request, mode)
    request.assumptions_used.extend(assumptions)

    sre = calculate_sre(request)

    bom = BOMResult(
        system_key="unknown",
        area_m2=0,
        panel_count=0,
        supports_per_panel=0,
        fixation_points=0,
    )
    can_calculate_bom = (
        request.familia is not None
        and request.thickness_mm is not None
        and request.uso is not None
        and (request.geometry.length_m is not None or request.geometry.panel_lengths)
    )

    if can_calculate_bom:
        length_m = request.geometry.length_m or 0
        width_m = request.geometry.width_m or 0
        if not width_m and request.geometry.panel_count:
            width_m = request.geometry.panel_count * 1.12

        if length_m > 0 and width_m > 0:
            bom = calculate_bom(
                familia=request.familia,
                sub_familia=request.sub_familia or "EPS",
                thickness_mm=request.thickness_mm,
                uso=request.uso,
                length_m=length_m,
                width_m=width_m,
                structure_type=request.structure_type or "metal",
                panel_count=request.geometry.panel_count,
                panel_lengths=request.geometry.panel_lengths or None,
                roof_type=request.roof_type,
                span_m=request.span_m,
            )

    pricing = PricingResult()
    if bom.panel_count > 0 and request.familia and request.thickness_mm:
        pricing = calculate_pricing(
            bom=bom,
            familia=request.familia,
            sub_familia=request.sub_familia or "EPS",
            thickness_mm=request.thickness_mm,
            panel_area_m2=bom.area_m2,
            iva_mode=request.iva_mode,
        )

    validation = validate_quotation(
        request=request,
        sre=sre,
        bom=bom,
        pricing=pricing,
        mode=mode,
    )

    return {
        "mode": mode.value,
        "classification": classification.to_dict(),
        "request": request.to_dict(),
        "sre": sre.to_dict(),
        "bom": bom.to_dict(),
        "pricing": pricing.to_dict(),
        "validation": validation.to_dict(),
    }


def _run_sai_score(input_data: PanelinEngineInput) -> dict:
    mode = _resolve_mode(input_data.mode)
    output = process_quotation(
        text=input_data.text,
        force_mode=mode,
        client_name=input_data.client_name,
        client_phone=input_data.client_phone,
        client_location=input_data.client_location,
    )
    sai = calculate_sai(output)
    return {
        "quote_id": output.quote_id,
        "quote_status": output.status,
        "mode": output.mode,
        "sai": sai.to_dict(),
    }


_set_legacy_operation_ids()

api_router = APIRouter(prefix="/api", tags=["Panelin v4"])


@app.get("/")
async def root() -> dict:
    return {"service": "Panelin API", "version": "4.0.0", "status": "ok"}


@api_router.get("/health")
async def api_health() -> dict:
    return {"status": "healthy"}


@api_router.post("/quote")
async def quote(payload: PanelinEngineInput) -> dict:
    try:
        return {"ok": True, "data": await run_in_threadpool(_run_quote, payload)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@api_router.post("/validate")
async def validate(payload: PanelinEngineInput) -> dict:
    try:
        return {"ok": True, "data": await run_in_threadpool(_run_validation, payload)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@api_router.post("/sai-score")
async def sai_score(payload: PanelinEngineInput) -> dict:
    try:
        return {"ok": True, "data": await run_in_threadpool(_run_sai_score, payload)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
