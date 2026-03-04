"""
Panelin Agno — Workflow de Cotización Determinístico
=====================================================

Implementa el pipeline v4.0 de 7 pasos usando Agno Workflow.
El LLM SOLO interviene en el paso final de formateo de respuesta (~$0.02).
Todos los demás pasos son funciones Python puras ($0.00 cada uno).

Arquitectura:
    Step 1: classify   → classify_request()      — $0.00
    Step 2: parse      → parse_request()         — $0.00
    Step 3: sre        → calculate_sre()         — $0.00
    Router: bom_router → salta BOM si accesorios_only
    Step 4: bom        → calculate_bom()         — $0.00
    Step 5: pricing    → calculate_pricing()     — $0.00
    Step 6: validate   → validate_quotation()    — $0.00
    Step 7: respond    → Agent LLM              — ~$0.02
                                          Total: ~$0.02 por cotización

El backend controla el orden — el LLM no decide la secuencia.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from agno.agent import Agent
from agno.db.postgres import PostgresDb
from agno.models.openai import OpenAIChat
from agno.workflow import Workflow
from agno.workflow.condition import Condition
from agno.workflow.router import Router
from agno.workflow.step import Step, StepInput, StepOutput

from panelin_v4.engine.bom_engine import BOMResult, calculate_bom
from panelin_v4.engine.classifier import RequestType, classify_request
from panelin_v4.engine.parser import parse_request
from panelin_v4.engine.pricing_engine import calculate_pricing
from panelin_v4.engine.quotation_engine import QuotationOutput, process_quotation
from panelin_v4.engine.sre_engine import QuotationLevel, calculate_sre
from panelin_v4.engine.validation_engine import validate_quotation

from src.core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Claves de estado de sesión (state keys para compartir datos entre Steps)
# ─────────────────────────────────────────────────────────────────────────────
SK_CLASSIFICATION = "classification"
SK_REQUEST = "parsed_request"
SK_SRE = "sre_result"
SK_BOM = "bom_result"
SK_PRICING = "pricing_result"
SK_VALIDATION = "validation_result"
SK_OUTPUT = "quotation_output"
SK_IS_ACCESSORIES_ONLY = "is_accessories_only"
SK_MODE = "operating_mode"


# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Clasificación — detecta tipo y modo de la solicitud
# ─────────────────────────────────────────────────────────────────────────────
def step_classify(step_input: StepInput) -> StepOutput:
    """Clasifica el tipo (roof/wall/accessories/update) y modo (info/pre/formal)."""
    text = step_input.get_input_as_string()
    classification = classify_request(text)

    is_accessories_only = classification.request_type == RequestType.ACCESSORIES_ONLY
    mode = (
        classification.operating_mode.value
        if hasattr(classification.operating_mode, "value")
        else str(classification.operating_mode)
    )

    result = {
        "tipo": (
            classification.request_type.value
            if hasattr(classification.request_type, "value")
            else str(classification.request_type)
        ),
        "modo": mode,
        "is_accessories_only": is_accessories_only,
    }

    if step_input.workflow_session and hasattr(step_input.workflow_session, "session_data"):
        step_input.workflow_session.session_data = step_input.workflow_session.session_data or {}
        step_input.workflow_session.session_data[SK_CLASSIFICATION] = result
        step_input.workflow_session.session_data[SK_IS_ACCESSORIES_ONLY] = is_accessories_only
        step_input.workflow_session.session_data[SK_MODE] = mode

    return StepOutput(
        content=json.dumps(result, ensure_ascii=False),
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Parseo — texto libre → QuoteRequest estructurado
# ─────────────────────────────────────────────────────────────────────────────
def step_parse(step_input: StepInput) -> StepOutput:
    """Parsea el texto libre en QuoteRequest con regex tolerante al español."""
    text = step_input.get_input_as_string()
    request = parse_request(text)
    geo = request.geometry
    cli = request.client
    request_dict = {
        "familia": request.familia,
        "sub_familia": request.sub_familia,
        "thickness_mm": request.thickness_mm,
        "uso": request.uso,
        "length_m": geo.length_m if geo else None,
        "width_m": geo.width_m if geo else None,
        "height_m": geo.height_m if geo else None,
        "panel_count": geo.panel_count if geo else None,
        "panel_lengths": geo.panel_lengths if geo else [],
        "structure_type": request.structure_type,
        "roof_type": request.roof_type,
        "span_m": request.span_m,
        "client_name": cli.name if cli else None,
        "client_phone": cli.phone if cli else None,
    }

    if step_input.workflow_session and hasattr(step_input.workflow_session, "session_data"):
        session_data = step_input.workflow_session.session_data or {}
        session_data[SK_REQUEST] = request_dict
        step_input.workflow_session.session_data = session_data

    return StepOutput(
        content=json.dumps(request_dict, ensure_ascii=False),
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3: SRE — Structural Risk Engine
# ─────────────────────────────────────────────────────────────────────────────
def step_sre(step_input: StepInput) -> StepOutput:
    """Calcula el score de riesgo estructural (0-100).

    Determina el nivel de cotización requerido y si se necesitan datos adicionales.
    """
    text = step_input.get_input_as_string()
    request = parse_request(text)
    sre = calculate_sre(request)

    sre_dict = {
        "score": sre.score,
        "level": sre.level.value if hasattr(sre.level, "value") else str(sre.level),
        "r_datos": sre.r_datos,
        "r_autoportancia": sre.r_autoportancia,
        "r_geometria": sre.r_geometria,
        "r_sistema": sre.r_sistema,
        "breakdown": getattr(sre, "breakdown", []),
        "recommendations": sre.recommendations,
        "alternative_thicknesses": getattr(sre, "alternative_thicknesses", []),
    }

    if step_input.workflow_session and hasattr(step_input.workflow_session, "session_data"):
        session_data = step_input.workflow_session.session_data or {}
        session_data[SK_SRE] = sre_dict
        step_input.workflow_session.session_data = session_data

    return StepOutput(
        content=json.dumps(sre_dict, ensure_ascii=False),
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 4: BOM — Bill of Materials
# ─────────────────────────────────────────────────────────────────────────────
def step_bom(step_input: StepInput) -> StepOutput:
    """Calcula el BOM (materiales y cantidades) desde bom_rules.json."""
    text = step_input.get_input_as_string()
    request = parse_request(text)

    geo = request.geometry
    bom = calculate_bom(
        familia=request.familia or "ISOROOF",
        sub_familia=request.sub_familia or "STANDARD",
        thickness_mm=request.thickness_mm or 50,
        uso=request.uso or "techo",
        length_m=(geo.length_m if geo and geo.length_m else 0.0),
        width_m=(geo.width_m if geo and geo.width_m else 0.0),
        structure_type=request.structure_type or "metal",
        panel_count=(geo.panel_count if geo else None),
        panel_lengths=(geo.panel_lengths if geo else None),
        roof_type=request.roof_type,
        span_m=request.span_m,
    )
    bom_dict = bom.to_dict()

    if step_input.workflow_session and hasattr(step_input.workflow_session, "session_data"):
        session_data = step_input.workflow_session.session_data or {}
        session_data[SK_BOM] = bom_dict
        step_input.workflow_session.session_data = session_data

    return StepOutput(
        content=json.dumps(bom_dict, ensure_ascii=False),
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Pricing — Precios desde KB (NUNCA inventa)
# ─────────────────────────────────────────────────────────────────────────────
def step_pricing(step_input: StepInput) -> StepOutput:
    """Aplica precios del KB a los ítems del BOM. IVA 22% siempre incluido."""
    text = step_input.get_input_as_string()
    request = parse_request(text)

    geo_p = request.geometry
    bom = calculate_bom(
        familia=request.familia or "ISOROOF",
        sub_familia=request.sub_familia or "STANDARD",
        thickness_mm=request.thickness_mm or 50,
        uso=request.uso or "techo",
        length_m=(geo_p.length_m if geo_p and geo_p.length_m else 0.0),
        width_m=(geo_p.width_m if geo_p and geo_p.width_m else 0.0),
        structure_type=request.structure_type or "metal",
        panel_count=(geo_p.panel_count if geo_p else None),
    )

    pricing = calculate_pricing(
        bom=bom,
        familia=request.familia or "ISOROOF",
        sub_familia=request.sub_familia or "STANDARD",
        thickness_mm=request.thickness_mm or 50,
        panel_area_m2=bom.area_m2,
        iva_mode="incluido",
    )
    pricing_dict = pricing.to_dict()

    if step_input.workflow_session and hasattr(step_input.workflow_session, "session_data"):
        session_data = step_input.workflow_session.session_data or {}
        session_data[SK_PRICING] = pricing_dict
        step_input.workflow_session.session_data = session_data

    return StepOutput(
        content=json.dumps(pricing_dict, ensure_ascii=False),
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Validación — 4 capas (Integridad, Técnica, Comercial, Matemática)
# ─────────────────────────────────────────────────────────────────────────────
def step_validate(step_input: StepInput) -> StepOutput:
    """Ejecuta las 4 capas de validación sobre la cotización calculada."""
    text = step_input.get_input_as_string()
    request = parse_request(text)
    sre = calculate_sre(request)
    geo_v = request.geometry
    bom = calculate_bom(
        familia=request.familia or "ISOROOF",
        sub_familia=request.sub_familia or "STANDARD",
        thickness_mm=request.thickness_mm or 50,
        uso=request.uso or "techo",
        length_m=(geo_v.length_m if geo_v and geo_v.length_m else 0.0),
        width_m=(geo_v.width_m if geo_v and geo_v.width_m else 0.0),
        structure_type=request.structure_type or "metal",
    )
    pricing = calculate_pricing(
        bom=bom,
        familia=request.familia or "ISOROOF",
        sub_familia=request.sub_familia or "STANDARD",
        thickness_mm=request.thickness_mm or 50,
        panel_area_m2=bom.area_m2,
        iva_mode="incluido",
    )

    classification = classify_request(text)
    mode = (
        classification.operating_mode.value
        if hasattr(classification.operating_mode, "value")
        else "pre_cotizacion"
    )

    validation = validate_quotation(
        request=request,
        sre=sre,
        bom=bom,
        pricing=pricing,
        mode=mode,
    )

    validation_dict = {
        "is_valid": validation.is_valid,
        "can_emit_formal": validation.can_emit_formal,
        "blocking_issues": [
            {"capa": i.layer, "mensaje": i.message, "codigo": i.code,
             "severidad": i.severity.value if hasattr(i.severity, "value") else str(i.severity)}
            for i in validation.issues
            if hasattr(i.severity, "value") and i.severity.value == "critical"
        ],
        "warnings": [
            {"capa": i.layer, "mensaje": i.message, "codigo": i.code}
            for i in validation.issues
            if hasattr(i.severity, "value") and i.severity.value == "warning"
        ],
    }

    if step_input.workflow_session and hasattr(step_input.workflow_session, "session_data"):
        session_data = step_input.workflow_session.session_data or {}
        session_data[SK_VALIDATION] = validation_dict
        step_input.workflow_session.session_data = session_data

    return StepOutput(
        content=json.dumps(validation_dict, ensure_ascii=False),
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Router: Selección de ruta según tipo de solicitud
# ─────────────────────────────────────────────────────────────────────────────
_step_bom_obj = Step(
    name="bom",
    executor=step_bom,
    description="Calcula Bill of Materials desde bom_rules.json",
    skip_on_failure=False,
)
_step_pricing_obj = Step(
    name="pricing",
    executor=step_pricing,
    description="Aplica precios del KB a los ítems del BOM",
    skip_on_failure=False,
)
_step_validate_obj = Step(
    name="validate",
    executor=step_validate,
    description="Valida la cotización en 4 capas",
    skip_on_failure=True,
)


def route_after_sre(step_input: StepInput):
    """Router: determina si se ejecuta BOM o se salta directamente a pricing.

    Para solicitudes de accesorios (accessories_only), el BOM es trivial
    y se puede usar pricing directamente. Para el resto, BOM → pricing → validate.
    """
    previous_content = step_input.get_last_step_content()
    try:
        if previous_content:
            data = json.loads(previous_content) if isinstance(previous_content, str) else previous_content
            is_accessories = data.get("is_accessories_only", False)
            if is_accessories:
                return [_step_pricing_obj, _step_validate_obj]
    except (json.JSONDecodeError, AttributeError):
        pass
    return [_step_bom_obj, _step_pricing_obj, _step_validate_obj]


# ─────────────────────────────────────────────────────────────────────────────
# Agent de Respuesta (único paso con LLM)
# ─────────────────────────────────────────────────────────────────────────────
def _create_respond_agent() -> Agent:
    """Crea el agente LLM para formatear la respuesta final en español."""
    return Agent(
        name="PanelinResponder",
        model=OpenAIChat(
            id=settings.openai_model,
            api_key=settings.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        ),
        description="Formateador de cotizaciones técnico-comerciales para BMC Uruguay",
        instructions="""Sos el asistente de cotizaciones de BMC Uruguay.
Tu rol es FORMATEAR la cotización ya calculada por el motor determinístico.

REGLAS ABSOLUTAS:
1. NUNCA inventés precios — usá exactamente los valores del JSON recibido
2. NUNCA modificués cantidades de materiales
3. Respondé SIEMPRE en español rioplatense (vos, ustedes)
4. Presentá los datos de forma clara y profesional
5. Si hay precios faltantes (missing_prices), indicalo explícitamente
6. Incluí el total en USD con IVA 22% incluido

FORMATO DE RESPUESTA:
- Encabezado con cliente (si disponible) y tipo de obra
- Resumen ejecutivo: área, sistema, nivel de cotización
- Tabla de materiales con cantidades y precios
- Total general IVA incluido
- Advertencias o condiciones técnicas (si las hay)
- Próximos pasos según el modo (informativo/pre/formal)""",
        markdown=True,
        debug_mode=settings.debug,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Workflow Principal
# ─────────────────────────────────────────────────────────────────────────────
def create_quotation_workflow(session_id: Optional[str] = None, user_id: Optional[str] = None) -> Workflow:
    """Crea el workflow de cotización Panelin v4.0 con Agno.

    El workflow ejecuta el pipeline determinístico + 1 paso LLM para formateo.
    Costo total: ~$0.02 por cotización (solo el paso de respuesta usa LLM).

    Args:
        session_id: ID de sesión para persistencia en PostgreSQL (opcional)
        user_id: ID del usuario para asociar la sesión

    Returns:
        Workflow configurado con todos los pasos del pipeline
    """
    db = None
    if settings.agno_db_url:
        db = PostgresDb(
            db_url=settings.agno_db_url,
            session_table=settings.workflow_session_table,
        )

    respond_agent = _create_respond_agent()

    workflow = Workflow(
        name="panelin_quotation_v4",
        description="Pipeline determinístico de cotización para paneles BMC Uruguay",
        db=db,
        session_id=session_id,
        user_id=user_id,
        steps=[
            Step(
                name="classify",
                executor=step_classify,
                description="Clasifica tipo y modo de la solicitud",
                skip_on_failure=False,
            ),
            Step(
                name="parse",
                executor=step_parse,
                description="Parsea texto libre → QuoteRequest estructurado",
                skip_on_failure=False,
            ),
            Step(
                name="sre",
                executor=step_sre,
                description="Calcula Structural Risk Engine score (0-100)",
                skip_on_failure=False,
            ),
            Router(
                name="pipeline_router",
                choices=[_step_bom_obj, _step_pricing_obj, _step_validate_obj],
                selector=route_after_sre,
            ),
            Step(
                name="respond",
                agent=respond_agent,
                description="Formatea la respuesta final en español (único paso LLM)",
            ),
        ],
        debug_mode=settings.debug,
    )

    return workflow


async def run_quotation_workflow(
    text: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Ejecuta el workflow de cotización y retorna la respuesta formateada.

    Shortcut para uso en la API. Para control fino, usar create_quotation_workflow().

    Args:
        text: Texto de solicitud del usuario en español
        session_id: ID de sesión (para historial conversacional)
        user_id: ID del usuario

    Returns:
        Respuesta formateada en español con la cotización
    """
    workflow = create_quotation_workflow(session_id=session_id, user_id=user_id)
    result = await workflow.arun(text)
    if hasattr(result, "content"):
        return result.content
    return str(result)
