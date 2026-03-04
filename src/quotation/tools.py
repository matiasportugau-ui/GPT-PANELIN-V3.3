"""Agno tools wrapping Panelin domain and integration operations."""

from __future__ import annotations

from typing import Any

import httpx
from agno.tools import tool

from src.core.config import AppSettings
from src.quotation.service import QuotationService


def _extract_workflow_content(run_result: Any) -> dict[str, Any]:
    if hasattr(run_result, "content"):
        content = run_result.content
        if isinstance(content, dict):
            return content
        return {"assistant_response": str(content)}
    return {"assistant_response": str(run_result)}


def build_domain_tools(
    settings: AppSettings,
    service: QuotationService,
    workflow=None,
) -> list[Any]:
    """Build Agno tools for deterministic quotation operations."""

    @tool
    def cotizar_paneles(
        text: str,
        mode: str = "pre_cotizacion",
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> dict[str, Any]:
        """Genera una cotización técnico-comercial determinística usando Panelin v4."""
        artifacts = service.process(
            text=text,
            mode=mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )
        return service.response_payload(artifacts.output, artifacts.sai)

    @tool
    def validar_solicitud_paneles(
        text: str,
        mode: str = "pre_cotizacion",
    ) -> dict[str, Any]:
        """Valida integridad técnica/comercial sin generar una respuesta conversacional."""
        artifacts = service.process(text=text, mode=mode)
        return {
            "classification": artifacts.classification.to_dict(),
            "request": artifacts.request.to_dict(),
            "validation": artifacts.validation.to_dict(),
            "sre": artifacts.sre.to_dict(),
            "sai": artifacts.sai.to_dict(),
        }

    tools: list[Any] = [cotizar_paneles, validar_solicitud_paneles]

    if workflow is not None:

        @tool
        def ejecutar_workflow_panelin(
            text: str,
            mode: str = "pre_cotizacion",
            session_id: str | None = None,
            user_id: str | None = None,
            client_name: str | None = None,
            client_phone: str | None = None,
            client_location: str | None = None,
        ) -> dict[str, Any]:
            """Ejecuta el workflow Agno explícito (classify→parse→...→respond)."""
            result = workflow.run(
                input={
                    "text": text,
                    "mode": mode,
                    "client_name": client_name,
                    "client_phone": client_phone,
                    "client_location": client_location,
                },
                session_id=session_id,
                user_id=user_id,
            )
            return _extract_workflow_content(result)

        tools.append(ejecutar_workflow_panelin)

    return tools


def build_integration_tools(settings: AppSettings) -> list[Any]:
    """Build wrappers around legacy Wolf API routes for Sheets/PDF/catalog."""

    timeout = httpx.Timeout(20.0, connect=5.0)

    def _wolf_request(method: str, path: str, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if settings.wolf_api_key:
            headers["X-API-Key"] = settings.wolf_api_key
        url = f"{settings.wolf_api_url.rstrip('/')}{path}"
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method=method, url=url, json=json_payload, headers=headers)
            response.raise_for_status()
            return response.json()

    @tool
    def buscar_productos_catalogo(query: str, max_results: int = 5) -> dict[str, Any]:
        """Consulta /find_products del Wolf API para búsquedas rápidas de catálogo."""
        return _wolf_request("POST", "/find_products", {"query": query, "max_results": max_results})

    @tool
    def registrar_consulta_sheets(
        cliente: str,
        telefono: str,
        consulta: str,
        origen: str = "AGNO",
        direccion: str = "",
        comentarios: str = "",
    ) -> dict[str, Any]:
        """Escribe una nueva consulta comercial en Google Sheets vía /sheets/consultations."""
        payload = {
            "cliente": cliente,
            "telefono": telefono,
            "consulta": consulta,
            "origen": origen,
            "direccion": direccion,
            "comentarios": comentarios,
        }
        return _wolf_request("POST", "/sheets/consultations", payload)

    @tool
    def generar_pdf_cotizacion(payload: dict[str, Any]) -> dict[str, Any]:
        """Genera PDF comercial y sube a Drive vía /cotizaciones/generar_pdf."""
        return _wolf_request("POST", "/cotizaciones/generar_pdf", payload)

    return [buscar_productos_catalogo, registrar_consulta_sheets, generar_pdf_cotizacion]
