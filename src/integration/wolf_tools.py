from __future__ import annotations

from typing import Any

import httpx
from agno.tools.decorator import tool

from src.core.config import Settings


def _request_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    json_payload: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        response = client.request(method, url, headers=headers, json=json_payload)
        response.raise_for_status()
        return response.json()


def build_wolf_api_tools(settings: Settings) -> list[Any]:
    """Crea tools Agno para endpoints Wolf API existentes (fase de integracion)."""
    base_url = settings.wolf_api_base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if settings.wolf_api_key:
        headers["X-API-Key"] = settings.wolf_api_key

    @tool(
        name="wolf_find_products",
        description="Busca productos en Wolf API (/find_products).",
    )
    def wolf_find_products(query: str, max_results: int = 5) -> dict[str, Any]:
        return _request_json(
            method="POST",
            url=f"{base_url}/find_products",
            headers=headers,
            json_payload={"query": query, "max_results": max_results},
        )

    @tool(
        name="wolf_calculate_quote",
        description="Calcula cotizacion basica en Wolf API (/calculate_quote).",
    )
    def wolf_calculate_quote(
        product_id: str,
        length_m: float,
        width_m: float,
        quantity: int = 1,
        discount_percent: float = 0.0,
        include_accessories: bool = True,
        include_tax: bool = True,
        installation_type: str = "techo",
    ) -> dict[str, Any]:
        return _request_json(
            method="POST",
            url=f"{base_url}/calculate_quote",
            headers=headers,
            json_payload={
                "product_id": product_id,
                "length_m": length_m,
                "width_m": width_m,
                "quantity": quantity,
                "discount_percent": discount_percent,
                "include_accessories": include_accessories,
                "include_tax": include_tax,
                "installation_type": installation_type,
            },
        )

    @tool(
        name="wolf_add_consultation",
        description="Registra consulta en Google Sheets via Wolf API (/sheets/consultations).",
    )
    def wolf_add_consultation(
        cliente: str,
        consulta: str,
        telefono: str = "",
        direccion: str = "",
        origen: str = "AGNO",
        asignado: str = "",
        comentarios: str = "",
    ) -> dict[str, Any]:
        return _request_json(
            method="POST",
            url=f"{base_url}/sheets/consultations",
            headers=headers,
            json_payload={
                "cliente": cliente,
                "consulta": consulta,
                "telefono": telefono,
                "direccion": direccion,
                "origen": origen,
                "asignado": asignado,
                "comentarios": comentarios,
            },
        )

    @tool(
        name="wolf_generate_pdf",
        description="Genera PDF de cotizacion via Wolf API (/cotizaciones/generar_pdf).",
    )
    def wolf_generate_pdf(payload: dict[str, Any]) -> dict[str, Any]:
        return _request_json(
            method="POST",
            url=f"{base_url}/cotizaciones/generar_pdf",
            headers=headers,
            json_payload=payload,
            timeout=45.0,
        )

    return [
        wolf_find_products,
        wolf_calculate_quote,
        wolf_add_consultation,
        wolf_generate_pdf,
    ]
