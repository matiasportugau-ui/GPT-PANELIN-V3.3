"""
Panelin v5.0 — PDF Generation Tool

Wraps panelin_reports/pdf_generator.py as an Agno tool.
Generates professional PDF quotations with BMC branding.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from src.core.config import get_settings


def generate_quotation_pdf(
    quote_id: str,
    client_name: str,
    products: str,
    accessories: str = "[]",
    fixings: str = "[]",
    client_address: str = "",
    client_phone: str = "",
    shipping_usd: float = 0.0,
    comments: str = "",
) -> str:
    """Genera un PDF profesional de cotización con branding BMC Uruguay.

    Args:
        quote_id: ID de la cotización (ej: PV5-20260304-AB12CD34).
        client_name: Nombre del cliente.
        products: JSON array de productos (cada uno con name, quantity, unit_price, subtotal).
        accessories: JSON array de accesorios (mismo formato).
        fixings: JSON array de fijaciones (mismo formato).
        client_address: Dirección del cliente.
        client_phone: Teléfono del cliente.
        shipping_usd: Costo de flete en USD.
        comments: Comentarios adicionales.

    Returns:
        JSON con la ruta del PDF generado y metadata.
    """
    settings = get_settings()

    try:
        from panelin_reports.pdf_generator import generate_quotation_report

        products_list = json.loads(products) if isinstance(products, str) else products
        accessories_list = json.loads(accessories) if isinstance(accessories, str) else accessories
        fixings_list = json.loads(fixings) if isinstance(fixings, str) else fixings

        output_dir = Path(settings.pdf_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{quote_id}.pdf")

        generate_quotation_report(
            output_path=output_path,
            client_name=client_name,
            client_address=client_address,
            client_phone=client_phone,
            products=products_list,
            accessories=accessories_list,
            fixings=fixings_list,
            shipping_usd=shipping_usd,
            comments=comments,
        )

        return json.dumps({
            "ok": True,
            "pdf_path": output_path,
            "quote_id": quote_id,
            "client_name": client_name,
        }, ensure_ascii=False)

    except ImportError:
        return json.dumps({
            "ok": False,
            "error": "panelin_reports module not available",
        })
    except Exception as e:
        return json.dumps({
            "ok": False,
            "error": str(e),
        })
