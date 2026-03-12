"""PDF quotation endpoints for Wolf API.

This module intentionally keeps a lightweight implementation that relies on
`panelin_reports.build_quote_pdf` and avoids runtime side-effects at import.
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.responses import Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    expected = os.getenv("WOLF_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="WOLF_API_KEY not configured")
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


class ClienteData(BaseModel):
    nombre: str = "A CONFIRMAR"
    telefono: str = "A CONFIRMAR"
    obra: str = "A coordinar"
    direccion: str = "A CONFIRMAR"


class ItemData(BaseModel):
    nombre: str
    largo: float
    cantidad: int
    area: float
    precio_m2: float
    total: float


class AccesorioData(BaseModel):
    nombre: str
    largo: Optional[float] = None
    cantidad: int
    precio_unit: float
    total: float


class FinancialsData(BaseModel):
    subtotal: float
    iva: float
    total_mat: float
    envio: Optional[float] = None
    envio_nota: Optional[str] = "a coordinar"
    total_general: float


class CotizacionRequest(BaseModel):
    cliente: ClienteData = Field(default_factory=ClienteData)
    items: list[ItemData]
    accesorios: Optional[list[AccesorioData]] = None
    financials: FinancialsData
    spec: Optional[dict[str, str]] = None
    condiciones: Optional[list[str]] = None


class CotizacionResponse(BaseModel):
    success: bool
    doc_num: str
    pdf_url: str
    pdf_download: str
    drive_path: str
    total_usd: float
    fecha: str
    validez: str


def _build_report_payload(data: CotizacionRequest) -> dict[str, Any]:
    products: list[dict[str, Any]] = []
    for item in data.items:
        products.append(
            {
                "name": item.nombre,
                "unit_base": "m²",
                "quantity": item.area if item.area > 0 else item.cantidad,
                "unit_price_usd": item.precio_m2,
                "total_usd": item.total,
                "total_m2": item.area,
            }
        )

    accessories: list[dict[str, Any]] = []
    for acc in data.accesorios or []:
        accessories.append(
            {
                "name": acc.nombre,
                "unit_base": "ml" if acc.largo else "unidad",
                "quantity": acc.cantidad * (acc.largo or 1),
                "unit_price_usd": acc.precio_unit,
                "total_usd": acc.total,
            }
        )

    comments = [(line, "normal") for line in (data.condiciones or [])]

    return {
        "client_name": data.cliente.nombre,
        "client_address": data.cliente.direccion,
        "client_phone": data.cliente.telefono,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "quote_description": data.cliente.obra,
        "products": products,
        "accessories": accessories,
        "shipping_usd": data.financials.envio or 0.0,
        "comments": comments,
    }


def _generate_pdf_file(data: CotizacionRequest, output_path: Path) -> Path:
    from panelin_reports import build_quote_pdf

    payload = _build_report_payload(data)
    build_quote_pdf(data=payload, output_path=str(output_path))
    return output_path


router = APIRouter(tags=["Cotizaciones PDF"])


@router.post("/cotizaciones/generar_pdf")
async def generar_pdf(data: CotizacionRequest, _: str = Depends(verify_api_key)) -> Response:
    try:
        now = datetime.now(timezone.utc)
        doc_num = f"BMC-{now.strftime('%Y%m%d-%H%M%S')}"
        fecha = now.strftime("%d/%m/%Y")
        validez = (now + timedelta(days=30)).strftime("%d/%m/%Y")

        with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _generate_pdf_file(data, tmp_path)
            pdf_bytes = tmp_path.read_bytes()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{doc_num}.pdf"',
                "X-Doc-Num": doc_num,
                "X-Fecha": fecha,
                "X-Validez": validez,
                "X-Total-USD": str(data.financials.total_general),
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {exc}") from exc


@router.post("/cotizaciones/preview_pdf")
async def preview_pdf(data: CotizacionRequest, _: str = Depends(verify_api_key)) -> Response:
    try:
        with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _generate_pdf_file(data, tmp_path)
            pdf_bytes = tmp_path.read_bytes()
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="preview.pdf"'},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error generando preview: {exc}") from exc
