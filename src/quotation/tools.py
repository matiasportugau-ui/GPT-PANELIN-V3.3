from __future__ import annotations

from typing import Any, Optional

from agno.tools.decorator import tool

from panelin_v4.engine.classifier import OperatingMode

from src.quotation.service import QuotationService

service = QuotationService()


MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


def _resolve_mode(mode: Optional[str]) -> Optional[OperatingMode]:
    if not mode:
        return None
    key = mode.strip().lower()
    if key not in MODE_MAP:
        raise ValueError(f"Modo invalido '{mode}'. Use: {', '.join(sorted(MODE_MAP))}")
    return MODE_MAP[key]


@tool(
    name="panelin_generate_quote",
    description="Genera cotizacion deterministica con pipeline v4 (sin inventar precios).",
)
def panelin_generate_quote(
    text: str,
    mode: str = "pre_cotizacion",
    client_name: Optional[str] = None,
    client_phone: Optional[str] = None,
    client_location: Optional[str] = None,
) -> dict[str, Any]:
    """Ejecuta el engine Panelin v4 y devuelve salida estructurada completa."""
    output = service.process(
        text=text,
        force_mode=_resolve_mode(mode),
        client_name=client_name,
        client_phone=client_phone,
        client_location=client_location,
    )
    return output.to_dict()


@tool(
    name="panelin_validate_quote",
    description="Valida una cotizacion Panelin y devuelve resumen tecnico/comercial.",
)
def panelin_validate_quote(
    text: str,
    mode: str = "pre_cotizacion",
) -> dict[str, Any]:
    """Ejecuta cotizacion y devuelve bloque de validaciones para QA."""
    output = service.process(text=text, force_mode=_resolve_mode(mode))
    return {
        "quote_id": output.quote_id,
        "status": output.status,
        "validation": output.validation,
        "warnings": output.validation.get("warnings", []),
        "critical_count": output.validation.get("critical_count", 0),
    }


@tool(
    name="panelin_calculate_sai",
    description="Calcula SAI (System Accuracy Index) para una cotizacion.",
)
def panelin_calculate_sai(
    text: str,
    mode: str = "pre_cotizacion",
) -> dict[str, Any]:
    """Calcula SAI sobre salida de cotizacion deterministica."""
    output = service.process(text=text, force_mode=_resolve_mode(mode))
    sai = service.sai(output)
    return {
        "quote_id": output.quote_id,
        "status": output.status,
        "sai": sai.to_dict(),
    }


@tool(
    name="panelin_batch_quotes",
    description="Procesa cotizaciones en lote con pipeline deterministico v4.",
)
def panelin_batch_quotes(
    requests: list[dict[str, Any]],
    mode: Optional[str] = None,
) -> dict[str, Any]:
    """Procesa batch y devuelve outputs serializados."""
    outputs = service.process_batch(requests=requests, force_mode=_resolve_mode(mode))
    return {"count": len(outputs), "results": [output.to_dict() for output in outputs]}


PANELIN_QUOTATION_TOOLS = [
    panelin_generate_quote,
    panelin_validate_quote,
    panelin_calculate_sai,
    panelin_batch_quotes,
]
