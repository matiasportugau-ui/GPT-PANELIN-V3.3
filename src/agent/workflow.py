"""PanelinWorkflow — Pipeline determinístico de cotizaciones v4 con Agno.

Pipeline de 7 pasos:
  1. classify   — Clasifica tipo de solicitud y modo (0 LLM, regex puro)
  2. parse      — Parsea texto libre → QuoteRequest estructurado (0 LLM, regex)
  3. sre        — Calcula riesgo estructural SRE (0 LLM, matemáticas)
  4. bom_router — Router condicional: si accessories_only, salta el paso BOM
  5. bom        — Calcula Bill of Materials (0 LLM, lookup paramétrico)
  6. pricing    — Calcula precios desde KB (0 LLM, lookup NUNCA inventa)
  7. validate   — Valida 4 capas de integridad (0 LLM, reglas)
  8. respond    — Agente LLM formatea la respuesta en español (~$0.02)

Costo por cotización: ~$0.00 pasos 1–7 + ~$0.02 paso 8 = ~$0.02 total.
"""
from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any, Optional

from agno.workflow.workflow import Workflow, Router
from agno.workflow.step import Step, StepInput, StepOutput
from agno.agent import Agent
from agno.models.openai import OpenAIChat

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Step executor functions (pure Python, $0.00 each)
# ─────────────────────────────────────────────────────────────────────────────

def _classify_step(step_input: StepInput) -> StepOutput:
    """Paso 1: Clasificar tipo y modo de la solicitud."""
    text = str(step_input.input or "")
    try:
        from panelin_v4.engine.classifier import classify_request
        result = classify_request(text)
        req_type = result.request_type.value if hasattr(result.request_type, "value") else str(result.request_type)
        mode = result.operating_mode.value if hasattr(result.operating_mode, "value") else str(result.operating_mode)
        return StepOutput(content={
            "type": req_type,
            "mode": mode,
            "has_roof": result.has_roof,
            "has_wall": result.has_wall,
            "has_accessories": result.has_accessories,
            "confidence": result.confidence,
            "raw_text": text,
        })
    except Exception as exc:
        logger.warning("classify_step error: %s", exc)
        return StepOutput(content={"type": "info_only", "mode": "informativo", "raw_text": text, "error": str(exc)})


def _parse_step(step_input: StepInput) -> StepOutput:
    """Paso 2: Parsear texto libre → QuoteRequest estructurado."""
    text = str(step_input.input or "")
    prev_outputs = step_input.previous_step_outputs or {}
    classify_c = (prev_outputs.get("classify") or StepOutput(content={})).content or {}

    try:
        from panelin_v4.engine.parser import parse_request
        req = parse_request(text)
        # Serialize to a dict the pipeline can use
        geo = req.geometry
        client = req.client
        d = {
            "familia": req.familia,
            "sub_familia": req.sub_familia,
            "thickness_mm": req.thickness_mm,
            "uso": req.uso,
            "structure_type": req.structure_type,
            "span_m": req.span_m,
            "length_m": geo.length_m if geo else None,
            "width_m": geo.width_m if geo else None,
            "height_m": geo.height_m if geo else None,
            "panel_count": geo.panel_count if geo else None,
            "panel_lengths": geo.panel_lengths if geo else [],
            "roof_type": req.roof_type,
            "include_accessories": req.include_accessories,
            "include_fixings": req.include_fixings,
            "include_shipping": req.include_shipping,
            "iva_mode": req.iva_mode,
            "raw_text": req.raw_text,
            "incomplete_fields": req.incomplete_fields,
            "assumptions_used": req.assumptions_used,
            "client_name": client.name if client else None,
            "client_phone": client.phone if client else None,
            "client_location": client.location if client else None,
            # Propagate classification
            "req_type": classify_c.get("type", "info_only"),
            "mode": classify_c.get("mode", "informativo"),
        }
        return StepOutput(content=d)
    except Exception as exc:
        logger.warning("parse_step error: %s", exc)
        return StepOutput(content={
            "error": str(exc),
            "req_type": classify_c.get("type", "info_only"),
            "mode": classify_c.get("mode", "informativo"),
        })


def _sre_step(step_input: StepInput) -> StepOutput:
    """Paso 3: Calcular Structural Risk Engine score."""
    prev_outputs = step_input.previous_step_outputs or {}
    parsed = (prev_outputs.get("parse") or StepOutput(content={})).content or {}

    try:
        from panelin_v4.engine.sre_engine import calculate_sre
        from panelin_v4.engine.parser import QuoteRequest, ProjectGeometry, ClientInfo
        geo = ProjectGeometry(
            length_m=parsed.get("length_m"),
            width_m=parsed.get("width_m"),
            height_m=parsed.get("height_m"),
            panel_count=parsed.get("panel_count"),
            panel_lengths=parsed.get("panel_lengths") or [],
        )
        client = ClientInfo(
            name=parsed.get("client_name"),
            phone=parsed.get("client_phone"),
            location=parsed.get("client_location"),
        )
        req = QuoteRequest(
            familia=parsed.get("familia"),
            sub_familia=parsed.get("sub_familia"),
            thickness_mm=parsed.get("thickness_mm"),
            uso=parsed.get("uso"),
            structure_type=parsed.get("structure_type"),
            span_m=parsed.get("span_m") or parsed.get("length_m"),
            geometry=geo,
            client=client,
            roof_type=parsed.get("roof_type"),
            iva_mode=parsed.get("iva_mode", "incluido"),
            raw_text=parsed.get("raw_text", ""),
        )
        result = calculate_sre(req)
        return StepOutput(content={
            "score": result.score,
            "level": result.level.value if hasattr(result.level, "value") else str(result.level),
            "r_datos": result.r_datos,
            "r_autoportancia": result.r_autoportancia,
            "r_geometria": result.r_geometria,
            "r_sistema": result.r_sistema,
            "breakdown": result.breakdown,
            "recommendations": result.recommendations,
            "alternative_thicknesses": result.alternative_thicknesses,
        })
    except Exception as exc:
        logger.warning("sre_step error: %s", exc)
        return StepOutput(content={"score": 50, "level": "technical_conditioned", "error": str(exc)})


def _bom_step(step_input: StepInput) -> StepOutput:
    """Paso 5a: Calcular Bill of Materials (solo si hay datos suficientes)."""
    prev_outputs = step_input.previous_step_outputs or {}
    parsed = (prev_outputs.get("parse") or StepOutput(content={})).content or {}

    familia = parsed.get("familia", "")
    thickness = parsed.get("thickness_mm")
    length_m = parsed.get("length_m")
    width_m = parsed.get("width_m")
    uso = parsed.get("uso") or "techo"

    if not familia or not thickness:
        return StepOutput(content={"error": "Falta familia o espesor para calcular BOM", "items": []})
    if not length_m or not width_m:
        return StepOutput(content={"error": "Faltan dimensiones (largo/ancho) para calcular BOM", "items": []})

    try:
        from panelin_v4.engine.bom_engine import calculate_bom
        result = calculate_bom(
            familia=familia,
            sub_familia=parsed.get("sub_familia") or "EPS",
            thickness_mm=int(thickness),
            length_m=float(length_m),
            width_m=float(width_m),
            uso=uso,
            structure_type=parsed.get("structure_type") or "metal",
            roof_type=parsed.get("roof_type"),
            panel_count=parsed.get("panel_count"),
            panel_lengths=parsed.get("panel_lengths"),
        )
        # Serialize BOMResult
        return StepOutput(content={
            "system_key": result.system_key,
            "area_m2": result.area_m2,
            "panel_count": result.panel_count,
            "supports_per_panel": result.supports_per_panel,
            "fixation_points": result.fixation_points,
            "items": [
                {
                    "tipo": i.tipo,
                    "referencia": i.referencia,
                    "sku": i.sku,
                    "name": i.name,
                    "quantity": i.quantity,
                    "unit": i.unit,
                    "formula_used": i.formula_used,
                }
                for i in result.items
            ],
            "warnings": result.warnings,
        })
    except Exception as exc:
        logger.warning("bom_step error: %s", exc)
        return StepOutput(content={"error": str(exc), "items": []})


def _get_bom_data_from_router(prev_outputs: dict) -> dict:
    """Extracts BOM data from inside the bom_router's nested step."""
    bom_router_out = prev_outputs.get("bom_router")
    if bom_router_out and hasattr(bom_router_out, "steps") and bom_router_out.steps:
        for inner_step_out in bom_router_out.steps:
            content = getattr(inner_step_out, "content", None)
            if isinstance(content, dict) and content.get("items") is not None:
                return content
    return {}


def _pricing_step(step_input: StepInput) -> StepOutput:
    """Paso 6: Calcular precios desde KB (NUNCA inventa precios)."""
    prev_outputs = step_input.previous_step_outputs or {}
    parsed = (prev_outputs.get("parse") or StepOutput(content={})).content or {}
    bom_data = _get_bom_data_from_router(prev_outputs)

    if not bom_data.get("items"):
        return StepOutput(content={"error": "Sin BOM para cotizar", "total_usd": 0.0, "items": []})

    try:
        from panelin_v4.engine.pricing_engine import calculate_pricing
        from panelin_v4.engine.bom_engine import BOMResult, BOMItem

        # Reconstruct BOMResult from dict
        items = [
            BOMItem(
                tipo=it["tipo"],
                referencia=it["referencia"],
                sku=it.get("sku"),
                name=it.get("name"),
                quantity=it.get("quantity", 0),
                unit=it.get("unit", "unid"),
                formula_used=it.get("formula_used", ""),
            )
            for it in bom_data.get("items", [])
        ]
        bom = BOMResult(
            system_key=bom_data.get("system_key", ""),
            area_m2=bom_data.get("area_m2", 0),
            panel_count=bom_data.get("panel_count", 0),
            supports_per_panel=bom_data.get("supports_per_panel", 0),
            fixation_points=bom_data.get("fixation_points", 0),
            items=items,
            warnings=bom_data.get("warnings", []),
        )

        result = calculate_pricing(
            bom=bom,
            familia=parsed.get("familia", ""),
            sub_familia=parsed.get("sub_familia") or "EPS",
            thickness_mm=int(parsed.get("thickness_mm") or 0),
            panel_area_m2=bom_data.get("area_m2"),
        )

        # Serialize PricingResult (actual field names: subtotal_total_usd, subtotal_panels_usd, etc.)
        return StepOutput(content={
            "total_usd": result.subtotal_total_usd,
            "panels_usd": result.subtotal_panels_usd,
            "accessories_usd": result.subtotal_accessories_usd,
            "iva_mode": result.iva_mode,
            "items": [
                {
                    "tipo": getattr(pi, "tipo", ""),
                    "referencia": getattr(pi, "referencia", ""),
                    "quantity": getattr(pi, "quantity", None),
                    "price_unit_usd": getattr(pi, "price_unit_usd", None),
                    "price_total_usd": getattr(pi, "price_total_usd", None),
                    "sku": getattr(pi, "sku", None),
                    "name": getattr(pi, "name", None),
                }
                for pi in (result.items or [])
            ],
            "warnings": result.warnings or [],
            "missing_prices": result.missing_prices or [],
        })
    except Exception as exc:
        logger.warning("pricing_step error: %s", exc)
        return StepOutput(content={"error": str(exc), "total_usd": 0.0, "items": []})


def _validate_step(step_input: StepInput) -> StepOutput:
    """Paso 7: Validar 4 capas (integridad, técnica, comercial, matemática)."""
    prev_outputs = step_input.previous_step_outputs or {}
    parsed = (prev_outputs.get("parse") or StepOutput(content={})).content or {}
    sre_data = (prev_outputs.get("sre") or StepOutput(content={})).content or {}
    bom_data = _get_bom_data_from_router(prev_outputs)
    pricing_data = (prev_outputs.get("pricing") or StepOutput(content={})).content or {}

    mode = parsed.get("mode", "pre_cotizacion")

    try:
        from panelin_v4.engine.validation_engine import validate_quotation
        from panelin_v4.engine.parser import QuoteRequest, ProjectGeometry, ClientInfo
        from panelin_v4.engine.sre_engine import SREResult, QuotationLevel
        from panelin_v4.engine.bom_engine import BOMResult, BOMItem
        from panelin_v4.engine.pricing_engine import PricingResult

        geo = ProjectGeometry(
            length_m=parsed.get("length_m"),
            width_m=parsed.get("width_m"),
            height_m=parsed.get("height_m"),
            panel_count=parsed.get("panel_count"),
            panel_lengths=parsed.get("panel_lengths") or [],
        )
        req = QuoteRequest(
            familia=parsed.get("familia"),
            sub_familia=parsed.get("sub_familia"),
            thickness_mm=parsed.get("thickness_mm"),
            uso=parsed.get("uso"),
            structure_type=parsed.get("structure_type"),
            span_m=parsed.get("span_m"),
            geometry=geo,
            roof_type=parsed.get("roof_type"),
            iva_mode=parsed.get("iva_mode", "incluido"),
            raw_text=parsed.get("raw_text", ""),
        )

        # Reconstruct SREResult
        sre = None
        if sre_data.get("score") is not None:
            try:
                level_str = sre_data.get("level", "technical_conditioned")
                level = QuotationLevel(level_str)
                sre = SREResult(
                    score=sre_data.get("score", 50),
                    level=level,
                    r_datos=sre_data.get("r_datos", 0),
                    r_autoportancia=sre_data.get("r_autoportancia", 0),
                    r_geometria=sre_data.get("r_geometria", 0),
                    r_sistema=sre_data.get("r_sistema", 0),
                )
            except Exception:
                sre = None

        # Reconstruct BOMResult
        bom = None
        if bom_data.get("items"):
            bom_items = [
                BOMItem(
                    tipo=it["tipo"],
                    referencia=it["referencia"],
                    sku=it.get("sku"),
                    name=it.get("name"),
                    quantity=it.get("quantity", 0),
                    unit=it.get("unit", "unid"),
                )
                for it in bom_data["items"]
            ]
            bom = BOMResult(
                system_key=bom_data.get("system_key", ""),
                area_m2=bom_data.get("area_m2", 0),
                panel_count=bom_data.get("panel_count", 0),
                supports_per_panel=bom_data.get("supports_per_panel", 0),
                fixation_points=bom_data.get("fixation_points", 0),
                items=bom_items,
                warnings=bom_data.get("warnings", []),
            )

        # Reconstruct PricingResult — always provide a valid object
        try:
            pricing = PricingResult(
                items=[],
                subtotal_panels_usd=pricing_data.get("panels_usd", 0) or 0,
                subtotal_accessories_usd=pricing_data.get("accessories_usd", 0) or 0,
                subtotal_total_usd=pricing_data.get("total_usd", 0) or 0,
                iva_mode=pricing_data.get("iva_mode", "incluido"),
                warnings=pricing_data.get("warnings", []),
                missing_prices=pricing_data.get("missing_prices", []),
            )
        except Exception:
            pricing = PricingResult(items=[], warnings=[], missing_prices=["error_reconstructing"])

        # SRE always required (can't be None)
        if sre is None:
            try:
                sre = SREResult(
                    score=50, level=QuotationLevel("technical_conditioned"),
                    r_datos=40, r_autoportancia=0, r_geometria=0, r_sistema=10,
                )
            except Exception:
                pass

        # BOM always required (can't be None)
        if bom is None:
            bom = BOMResult(
                system_key="unknown", area_m2=0, panel_count=0,
                supports_per_panel=0, fixation_points=0, items=[], warnings=[],
            )

        # mode must be OperatingMode enum
        try:
            from panelin_v4.engine.classifier import OperatingMode as OpMode
            try:
                op_mode = OpMode(mode)
            except ValueError:
                op_mode = OpMode.PRE_COTIZACION
        except Exception:
            op_mode = None  # type: ignore

        result = validate_quotation(request=req, sre=sre, bom=bom, pricing=pricing, mode=op_mode)
        return StepOutput(content={
            "is_valid": result.is_valid,
            "can_emit_formal": result.can_emit_formal,
            "autoportancia_status": result.autoportancia_status,
            "critical_count": result.critical_count,
            "warning_count": result.warning_count,
            "issues": [i.to_dict() for i in result.issues],
        })
    except Exception as exc:
        logger.warning("validate_step error: %s", exc)
        return StepOutput(content={"valid": False, "error": str(exc), "blocking_issues": [], "warnings": []})


def _build_respond_step(model_id: str = "gpt-4o", temperature: float = 0.2) -> Step:
    """Paso 8: Agente LLM formatea la respuesta en español (~$0.02)."""
    respond_agent = Agent(
        name="Panelin Responder",
        model=OpenAIChat(id=model_id, temperature=temperature),
        instructions=_RESPOND_AGENT_PROMPT,
        markdown=True,
    )

    def _respond_fn(step_input: StepInput) -> StepOutput:
        prev_outputs = step_input.previous_step_outputs or {}

        classify_c = (prev_outputs.get("classify") or StepOutput(content={})).content
        parse_c = (prev_outputs.get("parse") or StepOutput(content={})).content
        sre_c = (prev_outputs.get("sre") or StepOutput(content={})).content
        bom_c = _get_bom_data_from_router(prev_outputs)
        pricing_c = (prev_outputs.get("pricing") or StepOutput(content={})).content
        validate_c = (prev_outputs.get("validate") or StepOutput(content={})).content

        context = _format_pipeline_context(
            original_input=str(step_input.input or ""),
            classify=classify_c,
            parse=parse_c,
            sre=sre_c,
            bom=bom_c,
            pricing=pricing_c,
            validate=validate_c,
        )

        try:
            response = respond_agent.run(context)
            final_text = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("respond_agent error: %s", exc)
            final_text = _fallback_response(bom_c, pricing_c, validate_c)

        return StepOutput(content=final_text)

    return Step(name="respond", executor=_respond_fn)


# ─────────────────────────────────────────────────────────────────────────────
# BOM Router — salta BOM si el tipo es accessories_only
# ─────────────────────────────────────────────────────────────────────────────

_bom_step_obj = Step(name="bom", executor=_bom_step)


def _route_bom(step_input: StepInput) -> list:
    """Selector del Router: retorna [] para accessories_only, [bom_step] para el resto."""
    prev = step_input.previous_step_content
    if isinstance(prev, dict):
        req_type = prev.get("req_type", "")
        if req_type == "accessories_only":
            logger.debug("route_bom: accessories_only → saltando BOM")
            return []
    return [_bom_step_obj]


_bom_router = Router(
    name="bom_router",
    choices=[_bom_step_obj],
    selector=_route_bom,
)


# ─────────────────────────────────────────────────────────────────────────────
# Workflow factory
# ─────────────────────────────────────────────────────────────────────────────

def build_panelin_workflow(
    model_id: str = "gpt-4o",
    temperature: float = 0.2,
    db=None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Workflow:
    """Construye y retorna el workflow Panelin configurado."""
    respond_step = _build_respond_step(model_id=model_id, temperature=temperature)

    return Workflow(
        name="panelin_quotation",
        description="Pipeline determinístico de cotizaciones Panelin v4 — 7 pasos Python + 1 LLM",
        steps=[
            Step(name="classify", executor=_classify_step),
            Step(name="parse", executor=_parse_step),
            Step(name="sre", executor=_sre_step),
            _bom_router,
            Step(name="pricing", executor=_pricing_step),
            Step(name="validate", executor=_validate_step),
            respond_step,
        ],
        db=db,
        session_id=session_id,
        user_id=user_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Context formatting for LLM respond step
# ─────────────────────────────────────────────────────────────────────────────

def _format_pipeline_context(
    original_input: str,
    classify: Any,
    parse: Any,
    sre: Any,
    bom: Any,
    pricing: Any,
    validate: Any,
) -> str:
    """Formatea el contexto completo del pipeline para el LLM de respuesta."""
    parts = [
        "=== SOLICITUD ORIGINAL ===",
        original_input,
        "",
        "=== CLASIFICACIÓN ===",
        json.dumps(classify or {}, ensure_ascii=False, default=str),
        "",
        "=== PARSEO (QuoteRequest) ===",
        json.dumps(parse or {}, ensure_ascii=False, default=str),
        "",
        "=== RIESGO ESTRUCTURAL (SRE) ===",
        json.dumps(sre or {}, ensure_ascii=False, default=str),
        "",
        "=== BILL OF MATERIALS (BOM) ===",
        json.dumps(bom or {}, ensure_ascii=False, default=str),
        "",
        "=== PRECIOS (desde KB — IVA 22% incluido) ===",
        json.dumps(pricing or {}, ensure_ascii=False, default=str),
        "",
        "=== VALIDACIÓN ===",
        json.dumps(validate or {}, ensure_ascii=False, default=str),
    ]
    return "\n".join(parts)


def _fallback_response(bom: Any, pricing: Any, validate: Any) -> str:
    """Respuesta de emergencia si el LLM falla."""
    total = None
    if isinstance(pricing, dict):
        total = pricing.get("total_usd")
    if total:
        return f"Cotización procesada. Total estimado: USD {total:.2f} (IVA 22% incluido)."
    return "Cotización procesada. Por favor consulte con el equipo de ventas BMC Uruguay."


_RESPOND_AGENT_PROMPT = """Eres Panelin, el asistente técnico-comercial de BMC Uruguay especializado
en paneles de construcción (ISODEC, ISOPANEL, ISOROOF, ISOWALL, ISOFRIG).

Tu tarea es formatear la respuesta final al cliente en español, de manera profesional,
clara y útil, basándote en los resultados del pipeline de cotización que recibirás.

## REGLAS CRÍTICAS:
1. NUNCA inventes precios — usa SOLO los precios que aparecen en los datos de precios del pipeline
2. Si no hay precio disponible, dilo explícitamente y sugiere consultar con ventas BMC
3. Responde SIEMPRE en español
4. Sé profesional pero cercano — este es un cliente real de BMC Uruguay
5. Si hay advertencias de validación, menciónalas claramente pero sin alarmar innecesariamente
6. Si el SRE indica riesgo alto, recomienda consulta técnica

## ESTRUCTURA DE RESPUESTA SUGERIDA:
- Saludo y confirmación de lo que entendiste
- Resultado principal (BOM resumido o información solicitada)
- Precios (si disponibles, siempre con "IVA 22% incluido")
- Advertencias técnicas (si las hay)
- Próximos pasos sugeridos

## PARA COTIZACIONES FORMALES:
- Incluye número de cotización (quote_id) si está disponible
- Menciona que la cotización es válida sujeto a confirmación del equipo de ventas
- Solicita datos del cliente si no están completos (nombre, teléfono, dirección de obra)

Mantén la respuesta concisa pero completa. Usa formato markdown cuando sea útil.
"""
