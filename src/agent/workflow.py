"""
Panelin Agno — Workflow de Cotización (Pipeline Determinístico)
================================================================

Implementa el pipeline v4.0 como un Agno Workflow con 7 Steps Python-puros
(sin LLM, sin costo adicional) + 1 Step LLM final para formatear la respuesta.

Arquitectura:
    Usuario → Step[classify] → Step[parse] → Step[sre]
              → Router[bom_route] (completo vs. solo accesorios)
              → Step[pricing] → Step[validate]
              → Step[respond] (Agent LLM — ~$0.02)

Costo total por cotización: ~$0.02–0.03 (solo el Step respond usa LLM)
Los 7 pasos determinísticos: $0.00 cada uno.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from agno.workflow import (
    Router,
    Step,
    StepInput,
    StepOutput,
    Steps,
    Workflow,
)

logger = logging.getLogger(__name__)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_step_content(step_input: StepInput, step_name: str) -> Optional[Any]:
    """Obtiene el contenido de un paso previo por nombre."""
    if not step_input.previous_step_outputs:
        return None
    step_out = step_input.previous_step_outputs.get(step_name)
    return step_out.content if step_out else None


def _error_output(step_name: str, error: str) -> StepOutput:
    """Retorna un StepOutput de error sin detener el pipeline."""
    logger.warning(f"[{step_name}] {error}")
    return StepOutput(
        content={"error": error, "step": step_name},
        success=False,
        error=error,
    )


# ─── Step 1: Clasificar ──────────────────────────────────────────────────────

def step_classify(step_input: StepInput) -> StepOutput:
    """Clasifica el tipo de solicitud y el modo operativo.

    Análisis regex puro. Determina:
      - request_type: roof_system | wall_system | accessories_only | ...
      - operating_mode: informativo | pre_cotizacion | formal

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.classifier import classify_request

    text = step_input.get_input_as_string() or ""
    if not text:
        return _error_output("classify", "Texto de entrada vacío")

    classification = classify_request(text)
    return StepOutput(content=classification.to_dict(), success=True)


# ─── Step 2: Parsear ─────────────────────────────────────────────────────────

def step_parse(step_input: StepInput) -> StepOutput:
    """Parsea el texto libre en un QuoteRequest estructurado.

    Extrae: familia, espesor, uso, dimensiones, cliente, accesorios.
    Tolerante a ruido — nunca bloquea. Marca campos incompletos.

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.parser import parse_request

    text = step_input.get_input_as_string() or ""
    if not text:
        return _error_output("parse", "Texto de entrada vacío")

    request = parse_request(text)
    return StepOutput(content=request.to_dict(), success=True)


# ─── Step 3: SRE — Riesgo Estructural ────────────────────────────────────────

def step_sre(step_input: StepInput) -> StepOutput:
    """Calcula el Structural Risk Engine (SRE) score 0–100.

    Evalúa riesgo en 4 dimensiones: datos, autoportancia, geometría, sistema.
    Level: LOW | MEDIUM | HIGH | CRITICAL.

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.parser import parse_request, QuoteRequest
    from panelin_v4.engine.sre_engine import calculate_sre

    text = step_input.get_input_as_string() or ""
    request = parse_request(text)
    sre = calculate_sre(request)
    return StepOutput(content=sre.to_dict(), success=True)


# ─── Step 4a: BOM Completo (techos/paredes) ──────────────────────────────────

def step_bom(step_input: StepInput) -> StepOutput:
    """Genera el Bill of Materials (BOM) completo.

    Calcula paneles + accesorios según reglas paramétricas de bom_rules.json.
    Selección de accesorios por prioridad: familia > espesor > UNIVERSAL.

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.parser import parse_request
    from panelin_v4.engine.bom_engine import calculate_bom, BOMResult
    from panelin_v4.engine.classifier import classify_request, OperatingMode

    text = step_input.get_input_as_string() or ""
    request = parse_request(text)
    classification = classify_request(text)

    # Aplicar supuestos en modo pre_cotizacion
    if classification.operating_mode != OperatingMode.FORMAL:
        if request.uso in ("techo",) and request.span_m is None:
            request.span_m = 1.5
        if not request.structure_type:
            request.structure_type = "metal"

    can_calc = (
        request.familia
        and request.thickness_mm
        and request.uso
        and (request.geometry.length_m or request.geometry.panel_lengths)
    )

    if not can_calc:
        missing = []
        if not request.familia:
            missing.append("familia")
        if not request.thickness_mm:
            missing.append("espesor")
        if not request.uso:
            missing.append("uso")
        if not request.geometry.length_m:
            missing.append("dimensiones")
        return StepOutput(
            content={
                "system_key": "unknown",
                "area_m2": 0.0,
                "panel_count": 0,
                "supports_per_panel": 0,
                "fixation_points": 0,
                "items": [],
                "warnings": [f"Datos insuficientes para BOM: falta {', '.join(missing)}"],
            },
            success=True,
        )

    length_m = request.geometry.length_m or 0
    width_m = request.geometry.width_m or 0

    if not width_m and request.geometry.panel_count:
        width_m = request.geometry.panel_count * 1.12

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
    return StepOutput(content=bom.to_dict(), success=True)


# ─── Step 4b: Solo Accesorios (skip BOM completo) ────────────────────────────

def step_accessories_only(step_input: StepInput) -> StepOutput:
    """Maneja solicitudes de solo accesorios sin cálculo estructural.

    Para pedidos como "necesito goteros y silicona", omite el BOM de paneles.

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.parser import parse_request

    text = step_input.get_input_as_string() or ""
    request = parse_request(text)

    return StepOutput(
        content={
            "system_key": "accessories_only",
            "area_m2": 0.0,
            "panel_count": 0,
            "supports_per_panel": 0,
            "fixation_points": 0,
            "items": [],
            "warnings": [],
            "requested_accessories": request.raw_accessories_requested,
        },
        success=True,
    )


# ─── Router: ¿BOM completo o solo accesorios? ────────────────────────────────

def select_bom_route(step_input: StepInput) -> str:
    """Selector del Router: decide qué rama tomar según el tipo de solicitud.

    Returns:
        "bom_completo" para techos/paredes con cálculo estructural.
        "solo_accesorios" para pedidos de accesorios sueltos.
    """
    classification = _get_step_content(step_input, "classify")
    if classification:
        request_type = classification.get("request_type", "")
        if request_type == "accessories_only":
            return "solo_accesorios"
    return "bom_completo"


# ─── Step 5: Pricing ─────────────────────────────────────────────────────────

def step_pricing(step_input: StepInput) -> StepOutput:
    """Valúa el BOM con precios de la KB (NUNCA inventa precios).

    Precios de bromyros_pricing_master.json y accessories_catalog.json.
    IVA 22% ya incluido en todos los precios del catálogo.
    Si precio no existe → error explícito en missing_prices.

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.parser import parse_request
    from panelin_v4.engine.bom_engine import BOMResult, BOMItem
    from panelin_v4.engine.pricing_engine import calculate_pricing, PricingResult

    text = step_input.get_input_as_string() or ""
    request = parse_request(text)

    # Reconstruir BOM desde el paso previo
    bom_data = _get_step_content(step_input, "bom_completo") or _get_step_content(step_input, "solo_accesorios")
    if not bom_data:
        return StepOutput(content=PricingResult().to_dict(), success=True)

    bom = BOMResult(
        system_key=bom_data.get("system_key", "unknown"),
        area_m2=bom_data.get("area_m2", 0.0),
        panel_count=bom_data.get("panel_count", 0),
        supports_per_panel=bom_data.get("supports_per_panel", 0),
        fixation_points=bom_data.get("fixation_points", 0),
        items=[
            BOMItem(
                tipo=i["tipo"],
                referencia=i["referencia"],
                sku=i.get("sku"),
                name=i.get("name"),
                quantity=i.get("quantity", 0),
                unit=i.get("unit", "unid"),
                formula_used=i.get("formula_used", ""),
                notes=i.get("notes", ""),
            )
            for i in bom_data.get("items", [])
        ],
        warnings=bom_data.get("warnings", []),
    )

    if bom.panel_count == 0 and not bom.items:
        return StepOutput(content=PricingResult().to_dict(), success=True)

    pricing = calculate_pricing(
        bom=bom,
        familia=request.familia or "ISODEC",
        sub_familia=request.sub_familia or "EPS",
        thickness_mm=request.thickness_mm or 100,
        panel_area_m2=bom.area_m2,
        iva_mode=request.iva_mode,
    )
    return StepOutput(content=pricing.to_dict(), success=True)


# ─── Step 6: Validar ─────────────────────────────────────────────────────────

def step_validate(step_input: StepInput) -> StepOutput:
    """Validación multicapa: Integridad, Técnica, Comercial, Matemática.

    En modo pre_cotizacion: no bloquea (solo warnings).
    En modo formal: bloquea si hay errores críticos.

    $0.00 — sin LLM.
    """
    from panelin_v4.engine.parser import parse_request
    from panelin_v4.engine.classifier import classify_request, OperatingMode
    from panelin_v4.engine.sre_engine import calculate_sre
    from panelin_v4.engine.bom_engine import BOMResult, BOMItem
    from panelin_v4.engine.pricing_engine import PricingResult, PricedItem
    from panelin_v4.engine.validation_engine import validate_quotation

    text = step_input.get_input_as_string() or ""
    request = parse_request(text)
    classification = classify_request(text)
    sre = calculate_sre(request)

    # Reconstruir BOM y Pricing desde pasos previos
    bom_data = _get_step_content(step_input, "bom_completo") or _get_step_content(step_input, "solo_accesorios") or {}
    bom = BOMResult(
        system_key=bom_data.get("system_key", "unknown"),
        area_m2=bom_data.get("area_m2", 0.0),
        panel_count=bom_data.get("panel_count", 0),
        supports_per_panel=bom_data.get("supports_per_panel", 0),
        fixation_points=bom_data.get("fixation_points", 0),
        warnings=bom_data.get("warnings", []),
    )

    pricing_data = _get_step_content(step_input, "pricing") or {}
    pricing = PricingResult(
        subtotal_panels_usd=pricing_data.get("subtotal_panels_usd", 0.0),
        subtotal_accessories_usd=pricing_data.get("subtotal_accessories_usd", 0.0),
        subtotal_total_usd=pricing_data.get("subtotal_total_usd", 0.0),
        missing_prices=pricing_data.get("missing_prices", []),
    )

    validation = validate_quotation(
        request=request,
        sre=sre,
        bom=bom,
        pricing=pricing,
        mode=classification.operating_mode,
    )
    return StepOutput(content=validation.to_dict(), success=True)


# ─── Ensamblar el Workflow ────────────────────────────────────────────────────

def build_quotation_workflow(
    db=None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Workflow:
    """Construye el workflow de cotización Panelin.

    Args:
        db: Instancia de PostgresDb para persistencia de sesiones.
        session_id: ID de sesión (para continuación de conversación).
        user_id: ID del usuario (para historial).

    Returns:
        Workflow listo para usar con workflow.run(input=texto).

    Costo: ~$0.00 por todos los pasos determinísticos.
           (El step de respuesta LLM vive en el Agent conversacional, no aquí)
    """
    bom_steps = Steps(
        steps=[
            Step(name="bom_completo", executor=step_bom),
            Step(name="pricing", executor=step_pricing),
        ]
    )

    accessories_step = Steps(
        steps=[
            Step(name="solo_accesorios", executor=step_accessories_only),
            Step(name="pricing", executor=step_pricing),
        ]
    )

    return Workflow(
        id="panelin-cotizacion-v4",
        name="Panelin Pipeline v4.0",
        description=(
            "Pipeline determinístico de cotizaciones BMC Uruguay. "
            "7 pasos Python puro + storage PostgreSQL para sesiones."
        ),
        db=db,
        session_id=session_id,
        user_id=user_id,
        steps=[
            Step(name="classify", executor=step_classify),
            Step(name="parse", executor=step_parse),
            Step(name="sre", executor=step_sre),
            Router(
                name="bom_router",
                choices=[bom_steps, accessories_step],
                selector=select_bom_route,
            ),
            Step(name="validate", executor=step_validate),
        ],
        stream=False,
        cache_session=True,
        add_workflow_history_to_steps=True,
    )


def run_quotation_pipeline(
    text: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """Ejecuta el pipeline completo y retorna todos los resultados por paso.

    Args:
        text: Texto libre de la solicitud de cotización en español.
        session_id: ID de sesión para persistencia conversacional.
        user_id: ID del usuario.
        db: PostgresDb para almacenar sesión.

    Returns:
        Dict con resultados de cada paso: classify, parse, sre, bom, pricing, validate.
    """
    workflow = build_quotation_workflow(db=db, session_id=session_id, user_id=user_id)

    output = workflow.run(input=text)

    # Extraer resultados de cada paso
    results = {}
    if output and hasattr(output, "steps") and output.steps:
        for step_out in output.steps:
            if step_out.step_name:
                results[step_out.step_name] = step_out.content

    # Si no hay resultados estructurados, usar el fallback del quotation_engine
    if not results:
        from src.quotation.service import QuotationRequest, get_quotation_service
        service = get_quotation_service()
        result = service.calculate(QuotationRequest(text=text, session_id=session_id))
        results = result.data

    return results
