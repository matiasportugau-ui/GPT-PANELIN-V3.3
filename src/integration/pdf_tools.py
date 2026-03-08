"""
Panelin Agno — PDF Generation Tool

Wraps the existing panelin_reports PDF generator as an Agno tool.
Generates professional BMC Uruguay quotation PDFs.
"""

from __future__ import annotations

import json
import os
from typing import Optional


def generate_quotation_pdf(
    quotation_json: str,
    client_name: str = "",
    upload_to_drive: bool = False,
) -> str:
    """Genera un PDF de cotización profesional BMC Uruguay.

    Args:
        quotation_json: JSON string con los datos completos de la cotización
            (output de generate_quotation).
        client_name: Nombre del cliente para el encabezado del PDF.
        upload_to_drive: Si True, sube el PDF a Google Drive y devuelve el link.

    Returns:
        JSON con la ruta del PDF generado y opcionalmente el link de Drive.
    """
    try:
        data = json.loads(quotation_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "JSON de cotización inválido"})

    output_dir = os.environ.get("PDF_OUTPUT_DIR", "panelin_reports/output")
    os.makedirs(output_dir, exist_ok=True)

    quote_id = data.get("quote_id", "PV5-DRAFT")
    filename = f"{quote_id}.pdf"
    filepath = os.path.join(output_dir, filename)

    try:
        from panelin_reports import generate_quotation_pdf as _gen_pdf

        _gen_pdf(
            quotation_data=data,
            output_path=filepath,
            client_name=client_name,
        )
    except ImportError:
        _generate_simple_pdf(data, filepath, client_name)
    except Exception as e:
        return json.dumps({"error": f"Error generando PDF: {e}"})

    result = {
        "ok": True,
        "filepath": filepath,
        "filename": filename,
        "quote_id": quote_id,
    }

    if upload_to_drive:
        try:
            from wolf_api.drive_uploader import upload_pdf, ensure_folder_structure

            folder_id = ensure_folder_structure(client_name or "Sin nombre")
            drive_url = upload_pdf(filepath, folder_id, filename)
            result["drive_url"] = drive_url
        except Exception as e:
            result["drive_upload_error"] = str(e)

    return json.dumps(result, ensure_ascii=False, indent=2)


def _generate_simple_pdf(data: dict, filepath: str, client_name: str) -> None:
    """Fallback PDF generation using ReportLab directly."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.colors import HexColor

    doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>BMC Uruguay — Cotización {data.get('quote_id', '')}</b>", styles["Title"]))
    elements.append(Spacer(1, 10 * mm))

    if client_name:
        elements.append(Paragraph(f"<b>Cliente:</b> {client_name}", styles["Normal"]))

    mode = data.get("mode", "pre_cotizacion")
    elements.append(Paragraph(f"<b>Modo:</b> {mode}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Fecha:</b> {data.get('timestamp', '')}", styles["Normal"]))
    elements.append(Spacer(1, 5 * mm))

    pricing = data.get("pricing", {})
    items = pricing.get("items", [])
    if items:
        table_data = [["Item", "Cantidad", "Precio Unit.", "Subtotal"]]
        for item in items:
            table_data.append([
                item.get("name") or item.get("tipo", ""),
                str(item.get("quantity", 0)),
                f"USD {item.get('unit_price_usd', 0):.2f}",
                f"USD {item.get('subtotal_usd', 0):.2f}",
            ])
        table_data.append(["", "", "TOTAL", f"USD {pricing.get('subtotal_total_usd', 0):.2f}"])

        t = Table(table_data, colWidths=[200, 60, 80, 80])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("Precios incluyen IVA 22%. Cotización válida por 15 días.", styles["Normal"]))
    elements.append(Paragraph("BMC Uruguay — www.bmcuruguay.com.uy", styles["Normal"]))

    doc.build(elements)
