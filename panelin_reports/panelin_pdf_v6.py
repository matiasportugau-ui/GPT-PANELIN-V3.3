#!/usr/bin/env python3
"""
Panelin PDF v6 — Dual PDF Generator for BMC Uruguay
=====================================================

Consumes the v6 JSON structure (from GPT Panelín v6) and generates:
  1. Client Quotation PDF (cotización para el cliente)
  2. Internal Costing PDF (costeo interno con márgenes)

Usage:
    from panelin_reports.panelin_pdf_v6 import generate_v6_pdfs
    client_pdf, costeo_pdf = generate_v6_pdfs(v6_json, output_dir="output/")

    # Or from CLI:
    python -m panelin_reports.panelin_pdf_v6 input.json --output-dir output/

Version: 6.0
"""

import json
import os
import re
import sys
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)

from .pdf_styles import BMCStyles

IVA_RATE = Decimal("0.22")


def _d(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _fmt(val, decimals=2) -> str:
    """Format number with thousands separator and fixed decimals."""
    if val is None:
        return "—"
    n = float(val)
    if decimals == 0:
        return f"{n:,.0f}"
    return f"{n:,.{decimals}f}"


def _generate_quote_number() -> str:
    now = datetime.now()
    seq = int(now.strftime("%H%M"))
    return f"COT-{now.strftime('%Y%m%d')}-{seq:04d}"


def _parse_html_bold(text: str) -> str:
    """Convert <b> tags to ReportLab bold markup."""
    return text.replace("<b>", "<b>").replace("</b>", "</b>")


# ── Line calculations ───────────────────────────────────────────

def _calc_panel_lines(paneles: List[dict]) -> Tuple[list, Decimal, Decimal, Decimal]:
    """Calculate panel line items. Returns (rows, total_pvp, total_cost, total_m2)."""
    rows = []
    total_pvp = Decimal("0")
    total_cost = Decimal("0")
    total_m2 = Decimal("0")

    for p in paneles:
        largo = _d(p.get("largo_m"))
        cant = _d(p.get("cantidad"))
        ancho = _d(p.get("ancho_util_m"))
        pvp_m2 = _d(p.get("precio_m2"))
        cost_m2 = _d(p.get("costo_m2"))

        m2 = largo * ancho * cant
        line_pvp = m2 * pvp_m2
        line_cost = m2 * cost_m2

        total_pvp += line_pvp
        total_cost += line_cost
        total_m2 += m2

        rows.append({
            "nombre": p.get("nombre", ""),
            "seccion": p.get("seccion", ""),
            "largo_m": float(largo),
            "cantidad": int(cant),
            "m2": float(m2.quantize(Decimal("0.01"))),
            "pvp_m2": float(pvp_m2),
            "cost_m2": float(cost_m2),
            "total_pvp": float(line_pvp.quantize(Decimal("0.01"))),
            "total_cost": float(line_cost.quantize(Decimal("0.01"))),
        })

    return rows, total_pvp, total_cost, total_m2


def _calc_accessory_lines(accesorios: List[dict]) -> Tuple[list, Decimal, Decimal]:
    rows = []
    total_pvp = Decimal("0")
    total_cost = Decimal("0")

    for a in accesorios:
        largo = _d(a.get("largo_m"))
        cant = _d(a.get("cantidad"))
        pvp_ml = _d(a.get("precio_ml"))
        cost_ml = _d(a.get("costo_ml"))

        line_pvp = largo * cant * pvp_ml
        line_cost = largo * cant * cost_ml

        total_pvp += line_pvp
        total_cost += line_cost

        rows.append({
            "nombre": a.get("nombre", ""),
            "largo_m": float(largo),
            "cantidad": int(cant),
            "pvp_ml": float(pvp_ml),
            "cost_ml": float(cost_ml),
            "total_pvp": float(line_pvp.quantize(Decimal("0.01"))),
            "total_cost": float(line_cost.quantize(Decimal("0.01"))),
        })

    return rows, total_pvp, total_cost


def _calc_anclaje_lines(anclaje: List[dict]) -> Tuple[list, Decimal, Decimal]:
    rows = []
    total_pvp = Decimal("0")
    total_cost = Decimal("0")

    for a in anclaje:
        cant = _d(a.get("cantidad"))
        pvp_u = _d(a.get("precio_unit"))
        cost_u = _d(a.get("costo_real"))

        line_pvp = cant * pvp_u
        line_cost = cant * cost_u

        total_pvp += line_pvp
        total_cost += line_cost

        rows.append({
            "nombre": a.get("nombre", ""),
            "especificacion": a.get("especificacion", ""),
            "cantidad": float(cant),
            "pvp_unit": float(pvp_u),
            "cost_unit": float(cost_u),
            "total_pvp": float(line_pvp.quantize(Decimal("0.01"))),
            "total_cost": float(line_cost.quantize(Decimal("0.01"))),
        })

    return rows, total_pvp, total_cost


# ── Client PDF ───────────────────────────────────────────────────

def _build_client_pdf(data: dict, output_path: str, logo_path: Optional[str]) -> str:
    """Generate the client-facing quotation PDF."""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=9*mm,
    )
    story = []
    usable_width = A4[0] - 24*mm

    empresa = data.get("empresa", {})
    cotizacion = data.get("cotizacion", {})
    cliente = data.get("cliente", {})

    numero = cotizacion.get("numero") or _generate_quote_number()
    fecha = cotizacion.get("fecha", datetime.now().strftime("%d/%m/%Y"))
    titulo = cotizacion.get("titulo", "Cotización")

    # ── Header ──
    header_style = BMCStyles.get_header_style()

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path)
            aspect = logo.imageWidth / logo.imageHeight
            logo.drawHeight = 18*mm
            logo.drawWidth = min(18*mm * aspect, 55*mm)

            info_lines = (
                f"{empresa.get('nombre', 'BMC Uruguay')}<br/>"
                f"<font size='7'>{empresa.get('email', '')}<br/>"
                f"{empresa.get('web', '')}<br/>"
                f"{empresa.get('telefono', '')}<br/>"
                f"{empresa.get('ciudad', '')}</font>"
            )
            info_style = ParagraphStyle("EmpInfo", fontSize=9, leading=11)
            info_para = Paragraph(info_lines, info_style)

            right_lines = (
                f"<font size='8'>Fecha: {fecha}</font><br/>"
                f"<font size='10'><b>Cotización {titulo}</b></font><br/>"
                f"<font size='8'>N°: {numero}</font>"
            )
            right_style = ParagraphStyle("QuoteInfo", fontSize=9, leading=12, alignment=2)
            right_para = Paragraph(right_lines, right_style)

            ht = Table([[logo, info_para, right_para]],
                       colWidths=[60*mm, 55*mm, usable_width - 115*mm])
            ht.setStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])
            story.append(ht)
        except Exception:
            story.append(Paragraph(f"<b>Cotización {titulo}</b> — N° {numero}", header_style))
    else:
        story.append(Paragraph(f"<b>Cotización {titulo}</b> — N° {numero}", header_style))

    story.append(Spacer(1, 4*mm))

    # ── Client info ──
    ci_style = ParagraphStyle("CI", fontSize=9, spaceAfter=2)
    story.append(Paragraph(f"<b>Cliente:</b> {cliente.get('nombre', '')}", ci_style))
    story.append(Paragraph(f"<b>Dirección:</b> {cliente.get('direccion', '')}", ci_style))
    story.append(Paragraph(f"<b>Tel/cel:</b> {cliente.get('telefono', '')}", ci_style))
    story.append(Spacer(1, 4*mm))

    # ── Panels table ──
    panel_rows, pan_pvp, _, total_m2 = _calc_panel_lines(data.get("paneles", []))
    acc_rows, acc_pvp, _ = _calc_accessory_lines(data.get("accesorios", []))
    anc_rows, anc_pvp, _ = _calc_anclaje_lines(data.get("anclaje", []))

    table_data = [["Producto", "Largos (m)", "Cant", "Precio m² (USD)", "Total (USD)"]]
    current_section = None

    for r in panel_rows:
        if r["seccion"] != current_section:
            current_section = r["seccion"]
            table_data.append([current_section, "", "", "", ""])
        table_data.append([
            r["nombre"], _fmt(r["largo_m"]), str(r["cantidad"]),
            _fmt(r["pvp_m2"]), _fmt(r["total_pvp"]),
        ])

    if acc_rows:
        table_data.append(["Accesorios", "Largo (m)", "Cant", "Precio ML (USD)", "Total (USD)"])
        for r in acc_rows:
            table_data.append([
                r["nombre"], _fmt(r["largo_m"]), str(r["cantidad"]),
                _fmt(r["pvp_ml"]), _fmt(r["total_pvp"]),
            ])

    if anc_rows:
        table_data.append(["Anclaje / Fijaciones", "Especif.", "Cant", "P. Unit. (USD)", "Total (USD)"])
        for r in anc_rows:
            table_data.append([
                r["nombre"], r["especificacion"], _fmt(r["cantidad"], 0),
                _fmt(r["pvp_unit"]), _fmt(r["total_pvp"]),
            ])

    col_w = [72*mm, 25*mm, 15*mm, 35*mm, 35*mm]
    tbl = Table(table_data, colWidths=col_w, repeatRows=1)
    style = BMCStyles.get_table_style()
    BMCStyles.apply_alternating_rows(style, len(table_data))
    tbl.setStyle(style)
    story.append(tbl)
    story.append(Spacer(1, 4*mm))

    # ── Totals ──
    subtotal = pan_pvp + acc_pvp + anc_pvp
    traslado = data.get("traslado", {})
    traslado_cost = _d(traslado.get("costo")) if traslado.get("incluido") else Decimal("0")
    subtotal_with_traslado = subtotal + traslado_cost
    iva = (subtotal_with_traslado * IVA_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_final = subtotal_with_traslado + iva

    totals_data = [
        [f"Total M²", _fmt(float(total_m2)), "Sub-Total", _fmt(float(subtotal_with_traslado))],
        ["", "", "IVA 22%", _fmt(float(iva))],
        ["", "", "Materiales", _fmt(float(total_final))],
    ]

    traslado_nota = traslado.get("nota", "Traslado sin cotizar")
    if traslado.get("incluido"):
        totals_data.append(["", "", "Traslado", _fmt(float(traslado_cost))])
    else:
        totals_data.append(["", "", "Traslado sin cotizar", "—"])

    totals_data.append(["", "", "TOTAL U$S", _fmt(float(total_final + traslado_cost if traslado.get("incluido") else total_final))])

    tt = Table(totals_data, colWidths=[30*mm, 30*mm, 55*mm, 35*mm])
    tt.setStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('LINEABOVE', (2, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, -1), (-1, -1), 6),
    ])
    story.append(tt)
    story.append(Spacer(1, 4*mm))

    # ── Comments ──
    comentarios = data.get("comentarios", [])
    if comentarios:
        ct_style = ParagraphStyle("CT", fontSize=10, fontName='Helvetica-Bold', spaceAfter=4)
        story.append(Paragraph("Comentarios", ct_style))

        cm_style = ParagraphStyle("CM", fontSize=7.6, leading=9, leftIndent=5, spaceAfter=1.5)
        for c in comentarios:
            text = _parse_html_bold(c)
            story.append(Paragraph(f"• {text}", cm_style))

    story.append(Spacer(1, 4*mm))

    # ── Bank footer ──
    bank_data = [
        ["Depósito Bancario", f"Titular: {empresa.get('banco_titular', 'Metalog SAS')} — RUT: {empresa.get('banco_rut', '')}"],
        [f"{empresa.get('banco_tipo', 'Caja de Ahorro - BROU.')}",
         f"Número de Cuenta Dólares: {empresa.get('banco_cuenta', '')}"],
        [f"Por cualquier duda, consultar al {empresa.get('contacto_dudas', '')}",
         "Lea los Términos y Condiciones"],
    ]
    bt = Table(bank_data, colWidths=[usable_width/2, usable_width/2])
    bt.setStyle(BMCStyles.get_footer_grid_style())
    story.append(bt)

    doc.build(story)
    return output_path


# ── Costeo PDF ───────────────────────────────────────────────────

def _build_costeo_pdf(data: dict, output_path: str) -> str:
    """Generate the internal costing PDF with margins."""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=10*mm, bottomMargin=9*mm,
    )
    story = []
    usable_width = A4[0] - 24*mm

    cotizacion = data.get("cotizacion", {})
    cliente = data.get("cliente", {})
    numero = cotizacion.get("numero") or _generate_quote_number()
    fecha = cotizacion.get("fecha", datetime.now().strftime("%d/%m/%Y"))
    titulo = cotizacion.get("titulo", "")

    # ── Header ──
    h_style = ParagraphStyle("CH", fontSize=12, fontName='Helvetica-Bold', alignment=1, spaceAfter=4)
    story.append(Paragraph("BMC URUGUAY — DOCUMENTO INTERNO DE COSTEO", h_style))

    sub_style = ParagraphStyle("CS", fontSize=9, alignment=1, spaceAfter=2)
    story.append(Paragraph(f"Cotización: {numero} — {titulo}   |   Fecha: {fecha}", sub_style))
    story.append(Paragraph(f"Cliente: {cliente.get('nombre', '')}   |   Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style))

    warn_style = ParagraphStyle("CW", fontSize=8, fontName='Helvetica-BoldOblique',
                                textColor=colors.red, alignment=1, spaceAfter=6)
    story.append(Paragraph("CONFIDENCIAL — USO INTERNO EXCLUSIVO — NO COMPARTIR CON CLIENTE", warn_style))
    story.append(Spacer(1, 3*mm))

    def _margin_str(pvp, cost):
        if cost == 0:
            return "—"
        margin = pvp - cost
        pct = (margin / cost) * 100
        return f"${margin:,.2f} ({pct:.1f}%)"

    # ── Panels ──
    panel_rows, pan_pvp, pan_cost, _ = _calc_panel_lines(data.get("paneles", []))
    if panel_rows:
        story.append(Paragraph("<b>PANELES</b>", ParagraphStyle("S", fontSize=9, fontName='Helvetica-Bold', spaceAfter=2)))
        pt_data = [["Panel", "M²", "Cant", "Costo/m²", "Costo Total", "PVP Total", "Margen"]]
        for r in panel_rows:
            pt_data.append([
                r["nombre"][:35], _fmt(r["m2"]), str(r["cantidad"]),
                _fmt(r["cost_m2"]), _fmt(r["total_cost"]),
                _fmt(r["total_pvp"]), _margin_str(r["total_pvp"], r["total_cost"]),
            ])
        pt = Table(pt_data, colWidths=[50*mm, 18*mm, 12*mm, 22*mm, 22*mm, 22*mm, 30*mm], repeatRows=1)
        ps = BMCStyles.get_table_style()
        BMCStyles.apply_alternating_rows(ps, len(pt_data))
        pt.setStyle(ps)
        story.append(pt)
        story.append(Spacer(1, 3*mm))

    # ── Accessories ──
    acc_rows, acc_pvp, acc_cost = _calc_accessory_lines(data.get("accesorios", []))
    if acc_rows:
        story.append(Paragraph("<b>ACCESORIOS</b>", ParagraphStyle("S2", fontSize=9, fontName='Helvetica-Bold', spaceAfter=2)))
        at_data = [["Accesorio", "Largo", "Cant", "Costo/ml", "Costo Total", "PVP Total", "Margen"]]
        for r in acc_rows:
            at_data.append([
                r["nombre"][:35], _fmt(r["largo_m"]), str(r["cantidad"]),
                _fmt(r["cost_ml"]), _fmt(r["total_cost"]),
                _fmt(r["total_pvp"]), _margin_str(r["total_pvp"], r["total_cost"]),
            ])
        at = Table(at_data, colWidths=[50*mm, 18*mm, 12*mm, 22*mm, 22*mm, 22*mm, 30*mm], repeatRows=1)
        a_s = BMCStyles.get_table_style()
        BMCStyles.apply_alternating_rows(a_s, len(at_data))
        at.setStyle(a_s)
        story.append(at)
        story.append(Spacer(1, 3*mm))

    # ── Fixations ──
    anc_rows, anc_pvp, anc_cost = _calc_anclaje_lines(data.get("anclaje", []))
    if anc_rows:
        story.append(Paragraph("<b>ANCLAJE / FIJACIONES</b>", ParagraphStyle("S3", fontSize=9, fontName='Helvetica-Bold', spaceAfter=2)))
        ft_data = [["Anclaje / Fijación", "Espec.", "Cant", "Costo Unit.", "Costo Total", "PVP Total", "Margen"]]
        for r in anc_rows:
            ft_data.append([
                r["nombre"][:35], r["especificacion"], _fmt(r["cantidad"], 0),
                _fmt(r["cost_unit"]), _fmt(r["total_cost"]),
                _fmt(r["total_pvp"]), _margin_str(r["total_pvp"], r["total_cost"]),
            ])
        ft = Table(ft_data, colWidths=[50*mm, 18*mm, 12*mm, 22*mm, 22*mm, 22*mm, 30*mm], repeatRows=1)
        f_s = BMCStyles.get_table_style()
        BMCStyles.apply_alternating_rows(f_s, len(ft_data))
        ft.setStyle(f_s)
        story.append(ft)
        story.append(Spacer(1, 3*mm))

    # ── Financial summary ──
    total_cost = pan_cost + acc_cost + anc_cost
    total_pvp = pan_pvp + acc_pvp + anc_pvp
    total_margin = total_pvp - total_cost
    margin_pct = (total_margin / total_cost * 100) if total_cost > 0 else Decimal("0")
    iva = (total_pvp * IVA_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)

    story.append(Paragraph("<b>RESUMEN FINANCIERO</b>", ParagraphStyle("RF", fontSize=10, fontName='Helvetica-Bold', spaceAfter=4)))

    summary_data = [
        ["Categoría", "Costo Total", "PVP Total", "Margen $", "Margen %"],
        ["Paneles", _fmt(float(pan_cost)), _fmt(float(pan_pvp)),
         _fmt(float(pan_pvp - pan_cost)), f"{float((pan_pvp - pan_cost) / pan_cost * 100) if pan_cost else 0:.1f}%"],
        ["Accesorios", _fmt(float(acc_cost)), _fmt(float(acc_pvp)),
         _fmt(float(acc_pvp - acc_cost)), f"{float((acc_pvp - acc_cost) / acc_cost * 100) if acc_cost else 0:.1f}%"],
        ["Anclaje", _fmt(float(anc_cost)), _fmt(float(anc_pvp)),
         _fmt(float(anc_pvp - anc_cost)), f"{float((anc_pvp - anc_cost) / anc_cost * 100) if anc_cost else 0:.1f}%"],
        ["TOTAL (sin IVA)", _fmt(float(total_cost)), _fmt(float(total_pvp)),
         _fmt(float(total_margin)), f"{float(margin_pct):.1f}%"],
    ]

    st = Table(summary_data, colWidths=[35*mm, 30*mm, 30*mm, 30*mm, 25*mm])
    st.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BMCStyles.TABLE_HEADER_BG),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.4, BMCStyles.TABLE_GRID_COLOR),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])
    story.append(st)
    story.append(Spacer(1, 5*mm))

    # ── Bottom-line totals ──
    bl_style = ParagraphStyle("BL", fontSize=10, spaceAfter=3)
    story.append(Paragraph(f"<b>COSTO TOTAL (sin IVA)</b>: U$S {_fmt(float(total_cost))}", bl_style))
    story.append(Paragraph(f"<b>PVP TOTAL (sin IVA)</b>: U$S {_fmt(float(total_pvp))}", bl_style))
    story.append(Paragraph(f"<b>PVP TOTAL (con IVA)</b>: U$S {_fmt(float(total_pvp + iva))}", bl_style))
    story.append(Paragraph(f"<b>MARGEN BRUTO</b>: U$S {_fmt(float(total_margin))}", bl_style))
    story.append(Paragraph(f"<b>MARGEN %</b>: {float(margin_pct):.1f}%", bl_style))

    doc.build(story)
    return output_path


# ── Public API ───────────────────────────────────────────────────

def generate_v6_pdfs(
    data: dict,
    output_dir: str = "output",
    logo_path: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate both PDFs from a v6 JSON structure.

    Args:
        data: Parsed v6 JSON dict (empresa, cotizacion, cliente, paneles, etc.)
        output_dir: Directory for output PDFs
        logo_path: Path to BMC logo (auto-detected if None)

    Returns:
        Tuple of (client_pdf_path, costeo_pdf_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    if logo_path is None:
        logo_path = BMCStyles.find_logo_path()

    cotizacion = data.get("cotizacion", {})
    numero = cotizacion.get("numero")
    if not numero:
        numero = _generate_quote_number()
        data.setdefault("cotizacion", {})["numero"] = numero

    safe_num = re.sub(r'[^\w\-]', '_', numero)

    client_path = os.path.join(output_dir, f"BMC_Cotizacion_{safe_num}.pdf")
    costeo_path = os.path.join(output_dir, f"BMC_Costeo_INTERNO_{safe_num}.pdf")

    _build_client_pdf(data, client_path, logo_path)
    _build_costeo_pdf(data, costeo_path)

    return client_path, costeo_path


def generate_from_json_file(
    json_path: str,
    output_dir: str = "output",
    logo_path: Optional[str] = None,
) -> Tuple[str, str]:
    """Load v6 JSON from file and generate both PDFs."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return generate_v6_pdfs(data, output_dir, logo_path)


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Panelin PDF v6 Generator")
    parser.add_argument("json_file", help="Path to v6 JSON file")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--logo", default=None, help="Path to BMC logo")
    args = parser.parse_args()

    client, costeo = generate_from_json_file(args.json_file, args.output_dir, args.logo)
    print(f"Client PDF:  {client}")
    print(f"Costeo PDF:  {costeo}")
