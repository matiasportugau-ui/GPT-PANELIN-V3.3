"""Agno tools wrapping Panelin domain services."""

from __future__ import annotations

from typing import Any

from agno.tools import tool
from src.quotation.schemas import PanelinEngineInput
from src.quotation.service import QuotationService


def build_quotation_tools(service: QuotationService) -> list[Any]:
    """Create Agno tools bound to a QuotationService instance."""

    @tool(name="cotizar_panelin")
    def cotizar_panelin(
        text: str,
        mode: str = "pre_cotizacion",
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> dict[str, Any]:
        """Procesa una cotización completa con pipeline determinístico v4."""
        payload = PanelinEngineInput(
            text=text,
            mode=mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )
        return service.quote(payload)

    @tool(name="validar_cotizacion_panelin")
    def validar_cotizacion_panelin(
        text: str,
        mode: str = "pre_cotizacion",
    ) -> dict[str, Any]:
        """Ejecuta clasificación, parseo, SRE, BOM, pricing y validación."""
        payload = PanelinEngineInput(text=text, mode=mode)
        return service.validate(payload)

    @tool(name="sai_panelin")
    def sai_panelin(
        text: str,
        mode: str = "pre_cotizacion",
    ) -> dict[str, Any]:
        """Calcula SAI (System Accuracy Index) para una cotización."""
        payload = PanelinEngineInput(text=text, mode=mode)
        return service.sai_score(payload)

    @tool(name="buscar_productos_panelin")
    def buscar_productos_panelin(query: str, max_results: int = 10) -> dict[str, Any]:
        """Busca productos en el catálogo local de Panelin."""
        return service.search_products(query=query, max_results=max_results)

    @tool(name="generar_pdf_panelin")
    def generar_pdf_panelin(quote_data: dict[str, Any], file_prefix: str = "PANELIN") -> dict[str, Any]:
        """Genera un PDF de cotización en el filesystem local."""
        return service.generate_pdf(quote_data=quote_data, file_prefix=file_prefix)

    return [
        cotizar_panelin,
        validar_cotizacion_panelin,
        sai_panelin,
        buscar_productos_panelin,
        generar_pdf_panelin,
    ]

