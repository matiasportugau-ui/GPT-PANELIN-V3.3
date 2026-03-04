"""
Panelin v5.0 — PDF Generation Tool
=====================================

Wraps the existing panelin_reports PDF generator as an Agno tool.
Generates BMC-branded PDF quotations with ReportLab.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_quotation_pdf(
    quotation_json: str,
    output_filename: Optional[str] = None,
) -> str:
    """Genera un PDF de cotización profesional con marca BMC Uruguay.

    Args:
        quotation_json: JSON string con los datos completos de la cotización
            (output de quote_from_text o del workflow de cotización)
        output_filename: Nombre del archivo PDF (opcional, se genera automáticamente)

    Returns:
        JSON con la ruta del archivo PDF generado o error.
    """
    try:
        data = json.loads(quotation_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})

    quote_id = data.get("quote_id", "unknown")
    if output_filename is None:
        output_filename = f"cotizacion_{quote_id}.pdf"

    output_dir = Path("panelin_reports/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    try:
        from panelin_reports.pdf_generator import generate_quotation_pdf as _gen_pdf

        _gen_pdf(data, str(output_path))

        return json.dumps({
            "success": True,
            "pdf_path": str(output_path),
            "quote_id": quote_id,
            "filename": output_filename,
        }, ensure_ascii=False)
    except ImportError:
        return _fallback_generate(data, str(output_path), quote_id, output_filename)
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return json.dumps({
            "success": False,
            "error": str(e),
            "quote_id": quote_id,
        })


def _fallback_generate(data: dict, output_path: str, quote_id: str, filename: str) -> str:
    """Fallback PDF generation using ReportLab directly."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("BMC Uruguay — Cotización", styles["Title"]))
        elements.append(Spacer(1, 6 * mm))

        elements.append(Paragraph(f"<b>Quote ID:</b> {quote_id}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Estado:</b> {data.get('status', 'draft')}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Modo:</b> {data.get('mode', 'pre_cotizacion')}", styles["Normal"]))
        elements.append(Spacer(1, 4 * mm))

        pricing = data.get("pricing", {})
        items = pricing.get("items", [])
        if items:
            table_data = [["Tipo", "Cantidad", "Precio Unit.", "Subtotal"]]
            for item in items:
                table_data.append([
                    item.get("tipo", ""),
                    str(item.get("quantity", "")),
                    f"${item.get('unit_price_usd', 0):.2f}",
                    f"${item.get('subtotal_usd', 0):.2f}",
                ])
            table_data.append(["", "", "TOTAL", f"${pricing.get('subtotal_total_usd', 0):.2f}"])

            table = Table(table_data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)

        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(
            "Precios en USD con IVA 22% incluido. Cotización sujeta a confirmación.",
            styles["Normal"],
        ))

        doc.build(elements)

        return json.dumps({
            "success": True,
            "pdf_path": output_path,
            "quote_id": quote_id,
            "filename": filename,
            "generator": "fallback",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "quote_id": quote_id,
        })


PDF_TOOLS = [generate_quotation_pdf]
