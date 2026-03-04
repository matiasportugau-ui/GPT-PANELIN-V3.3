"""Agno tool wrappers for deterministic quotation domain logic."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from agno.tools import tool

from src.quotation.service import QuotationService


def build_quotation_tools(service: QuotationService | None = None) -> list[Any]:
    """Create Agno tool functions backed by the deterministic v4 engine."""
    quotation_service = service or QuotationService()

    @tool(
        name="panelin_calcular_cotizacion",
        description=(
            "Calcula una cotización técnico-comercial de paneles con BOM, pricing, "
            "validación y salida estructurada."
        ),
    )
    def calcular_cotizacion(
        text: str,
        mode: str = "pre_cotizacion",
        client_name: str | None = None,
        client_phone: str | None = None,
        client_location: str | None = None,
    ) -> dict:
        output = quotation_service.process(
            text=text,
            mode=mode,
            client_name=client_name,
            client_phone=client_phone,
            client_location=client_location,
        )
        return output.to_dict()

    @tool(
        name="panelin_validar_cotizacion",
        description="Ejecuta validaciones de integridad, técnica, comercial y matemática.",
    )
    def validar_cotizacion(
        text: str,
        mode: str = "pre_cotizacion",
    ) -> dict:
        output = quotation_service.process(text=text, mode=mode).to_dict()
        return {
            "quote_id": output["quote_id"],
            "mode": output["mode"],
            "classification": output["classification"],
            "request": output["request"],
            "sre": output["sre"],
            "validation": output["validation"],
        }

    @tool(
        name="panelin_calcular_sai",
        description="Calcula SAI (System Accuracy Index) para una cotización.",
    )
    def calcular_sai(text: str, mode: str = "pre_cotizacion") -> dict:
        output = quotation_service.process(text=text, mode=mode)
        sai = quotation_service.calculate_sai(output)
        return {
            "quote_id": output.quote_id,
            "mode": output.mode,
            "status": output.status,
            "sai": sai.to_dict(),
        }

    @tool(
        name="panelin_generar_pdf",
        description="Genera un PDF local de cotización profesional basado en salida de motor.",
    )
    def generar_pdf(quote_data: dict, output_filename: str | None = None) -> dict:
        from panelin_reports import build_quote_pdf

        quote = quotation_service.output_from_dict(quote_data)
        pricing_items = quote.pricing.get("items", [])

        products = []
        accessories = []
        for item in pricing_items:
            row = {
                "name": item.get("name") or item.get("tipo", ""),
                "unit_base": item.get("unit", "unidad"),
                "quantity": item.get("quantity", 0),
                "unit_price_usd": item.get("unit_price_usd", 0),
                "total_usd": item.get("subtotal_usd", 0),
            }
            if item.get("tipo") == "panel":
                products.append(row)
            else:
                accessories.append(row)

        request = quote.request
        client = request.get("client", {})
        payload = {
            "client_name": client.get("name", "A CONFIRMAR"),
            "client_address": client.get("location", "A CONFIRMAR"),
            "client_phone": client.get("phone", "A CONFIRMAR"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "quote_description": f"{request.get('familia', 'Panel')} {request.get('thickness_mm', '')}mm",
            "products": products,
            "accessories": accessories,
            "shipping_usd": 0.0,
            "comments": [(note, "normal") for note in quote.processing_notes],
        }

        if output_filename:
            output_path = Path(output_filename).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                output_path = Path(tmp.name)

        build_quote_pdf(payload, str(output_path))
        return {
            "ok": True,
            "quote_id": quote.quote_id,
            "pdf_path": str(output_path),
        }

    return [calcular_cotizacion, validar_cotizacion, calcular_sai, generar_pdf]
