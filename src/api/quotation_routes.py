"""
Panelin Agno — Rutas de Cotización REST
==========================================

API REST para cotizaciones que puede usarse desde:
- Custom GPT Actions (backward compatibility con Wolf API)
- Cualquier cliente HTTP
- El propio agente Agno via HTTP tools

Mantiene compatibilidad con los endpoints existentes (/calculate_quote, etc.)
mientras agrega nuevos endpoints del pipeline v4.0.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v4", tags=["Cotizaciones v4.0"])

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> None:
    """Valida el API key de la solicitud."""
    import hmac
    import os

    wolf_key = os.environ.get("WOLF_API_KEY", "")
    if not wolf_key:
        raise HTTPException(503, "WOLF_API_KEY no configurado")
    if not api_key or not hmac.compare_digest(api_key, wolf_key):
        raise HTTPException(401, "API key inválido o ausente")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class QuotationRequest(BaseModel):
    text: str = Field(..., description="Descripción libre del proyecto en español")
    mode: str = Field(
        default="pre_cotizacion",
        description="informativo | pre_cotizacion | formal",
    )
    client_name: Optional[str] = Field(None, description="Nombre del cliente")
    client_phone: Optional[str] = Field(None, description="Teléfono del cliente")
    client_location: Optional[str] = Field(None, description="Ubicación / departamento")
    session_id: Optional[str] = Field(None, description="ID de sesión para conversación")


class QuotationResponse(BaseModel):
    success: bool
    quote_id: Optional[str]
    mode: str
    status: str
    level: str
    confidence_score: float
    processing_ms: float
    summary: str
    data: Dict[str, Any]
    error: Optional[str] = None


class BatchQuotationRequest(BaseModel):
    requests: List[QuotationRequest]
    mode: Optional[str] = None


class ProductSearchRequest(BaseModel):
    query: str = Field(..., description="Término de búsqueda en el catálogo")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje del usuario en español")
    session_id: Optional[str] = Field(None, description="ID de sesión")
    user_id: Optional[str] = Field(None, description="ID del usuario")


class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/calculate_quote",
    response_model=QuotationResponse,
    summary="Calcular cotización",
    description="Ejecuta el pipeline determinístico v4.0. Reemplaza el endpoint legacy.",
)
async def calculate_quote(
    request: QuotationRequest,
    _: None = Depends(_require_api_key),
) -> QuotationResponse:
    from src.quotation.service import QuotationRequest as SvcRequest, get_quotation_service

    service = get_quotation_service()
    svc_request = SvcRequest(
        text=request.text,
        mode=request.mode,
        client_name=request.client_name,
        client_phone=request.client_phone,
        client_location=request.client_location,
        session_id=request.session_id,
    )

    result = service.calculate(svc_request)

    return QuotationResponse(
        success=result.success,
        quote_id=result.quote_id,
        mode=result.mode,
        status=result.status,
        level=result.level,
        confidence_score=result.confidence_score,
        processing_ms=result.processing_ms,
        summary=result.to_summary(),
        data=result.data,
        error=result.error,
    )


@router.post(
    "/calculate_batch",
    summary="Cotizaciones en batch",
)
async def calculate_batch(
    request: BatchQuotationRequest,
    _: None = Depends(_require_api_key),
) -> List[Dict[str, Any]]:
    from src.quotation.service import QuotationRequest as SvcRequest, get_quotation_service

    service = get_quotation_service()
    svc_requests = [
        SvcRequest(
            text=r.text,
            mode=r.mode,
            client_name=r.client_name,
            client_phone=r.client_phone,
            client_location=r.client_location,
        )
        for r in request.requests
    ]

    results = service.calculate_batch(svc_requests, mode=request.mode)
    return [r.to_dict() for r in results]


@router.post(
    "/search_products",
    summary="Buscar productos en catálogo",
)
async def search_products(
    request: ProductSearchRequest,
    _: None = Depends(_require_api_key),
) -> List[Dict[str, Any]]:
    from src.quotation.service import get_quotation_service

    service = get_quotation_service()
    return service.search_products(request.query)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat con el agente Panelin",
    description="Conversación con el agente Panelin. Mantiene contexto de sesión.",
)
async def chat(
    request: ChatRequest,
    _: None = Depends(_require_api_key),
) -> ChatResponse:
    """Endpoint de chat con el agente conversacional Panelin.

    El agente mantiene memoria de la conversación y puede:
    - Calcular cotizaciones
    - Buscar productos
    - Responder preguntas técnicas
    - Guiar al cliente por el proceso de cotización
    """
    from src.agent.panelin import build_panelin_agent

    db = None
    try:
        from src.app import _build_db
        db = _build_db()
    except Exception:
        pass

    agent = build_panelin_agent(
        session_id=request.session_id,
        user_id=request.user_id,
        db=db,
    )

    try:
        run_response = agent.run(request.message)
        response_text = run_response.content if hasattr(run_response, "content") else str(run_response)
        return ChatResponse(
            response=response_text,
            session_id=request.session_id or agent.session_id,
        )
    except Exception as exc:
        logger.exception(f"Error en chat: {exc}")
        raise HTTPException(500, f"Error interno del agente: {exc}")


@router.get(
    "/health",
    summary="Health check del pipeline v4.0",
)
async def health() -> Dict[str, Any]:
    """Verifica que el pipeline v4.0 esté operativo."""
    try:
        from src.quotation.service import QuotationRequest, get_quotation_service

        service = get_quotation_service()
        result = service.calculate(
            QuotationRequest(text="ISODEC 100mm techo 10x8 metros estructura metálica")
        )
        return {
            "status": "ok",
            "pipeline": "v4.0",
            "engine_test": result.success,
            "processing_ms": result.processing_ms,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
