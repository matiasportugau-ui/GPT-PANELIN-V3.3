"""
pdf_cotizacion.py — Endpoint para generar presupuestos PDF (BMC Uruguay)
POST /cotizaciones/generar_pdf
"""

import io
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)

from .drive_uploader import (
ensure_folder_structure, upload_pdf, get_drive_path,
generate_doc_number, sanitize_filename
)

logger = logging.getLogger("panelin.pdf")

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
  expected = os.getenv("WOLF_API_KEY", "mywolfykey123XYZ")
  if not api_key or api_key != expected:
    raise HTTPException(status_code=401, detail="Invalid API Key")
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
  items: List[ItemData]
  accesorios: Optional[List[AccesorioData]] = None
  financials: FinancialsData
  spec: Optional[Dict[str, str]] = None
  condiciones: Optional[List[str]] = None


class CotizacionResponse(BaseModel):
  success: bool
  doc_num: str
  pdf_url: str
  pdf_download: str
  drive_path: str
  total_usd: float
  fecha: str
  validez: str


NAVY   = HexColor("#0F2B46")
STEEL  = HexColor("#2C5F8A")
SKY    = HexColor("#E8F0F8")
AMBER  = HexColor("#D4872E")
SLATE  = HexColor("#3A3F47")
BORDER = HexColor("#D0D7DE")
WHITE  = white

BANK = {
  "titular": "Metalog SAS",
  "rut": "120403430012",
  "banco": "BROU",
  "tipo_cuenta": "Caja de Ahorro",
  "cuenta_usd": "110520638-00002",
  "consultas": "092 663 245",
}

DEFAULT_CONDITIONS = [
  "<b>Pendiente minima</b> recomendada en techo: 7%.",
  "BMC Uruguay suministra materiales y brinda asesoramiento tecnico. <b>No incluye instalacion/colocacion.</b>",
  "Entrega: retiro en planta o envio a coordinar. Costo de envio orientativo.",
  "<b>Forma de pago:</b> sena 60% al confirmar, saldo 40% previo a retiro. Con MP: recargo 11,9%.",
  "Entrega estimada: 10 a 15 dias habiles (sujeto a produccion).",
  "Al aceptar, confirma haber revisado medidas, cantidades, colores, valores y tipo de producto.",
  "Al recibir el material, verificar estado. No se aceptan devoluciones post-recepcion.",
]


class BMCPageTemplate:
  def __init__(self, doc_num: str, fecha: str, validez: str):
    self.doc_num = doc_num
    self.fecha = fecha
    self.validez = validez

  def __call__(self, canvas_obj, doc):
    canvas_obj.saveState()
    w, h = A4
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, h - 26*mm, w, 26*mm, fill=1, stroke=0)
    canvas_obj.setFillColor(AMBER)
    canvas_obj.rect(0, h - 27*mm, w, 1.2*mm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 20)
    canvas_obj.drawString(14*mm, h - 14*mm, "BMC")
    canvas_obj.setFont("Helvetica-Bold", 11)
    canvas_obj.drawString(38*mm, h - 14*mm, "URUGUAY")
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.drawString(14*mm, h - 20*mm, "Paneles Aislantes  &  Sistemas Constructivos")
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawRightString(w - 14*mm, h - 11*mm, "info@bmcuruguay.com.uy")
    canvas_obj.drawRightString(w - 14*mm, h - 16*mm, "www.bmcuruguay.com.uy")
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.drawRightString(w - 14*mm, h - 21.5*mm, "WhatsApp: 092 663 245  |  Tel: 4222 4031")
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, 0, w, 10*mm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica", 6.5)
    canvas_obj.drawString(14*mm, 3.5*mm,
    f"Presupuesto {self.doc_num}  ·  Emitido {self.fecha}  ·  Valido hasta {self.validez}  ·  Precios en USD")
    canvas_obj.drawRightString(w - 14*mm, 3.5*mm, f"Pag. {doc.page}")
    canvas_obj.restoreState()


  def fmt(n: float) -> str:
    """Format number with comma thousands: 4,362.71"""
    return f"{n:,.2f}"


def generate_pdf_bytes(data: CotizacionRequest, doc_num: str) -> bytes:
  """Generate the complete PDF as bytes (in memory, no disk I/O)."""
  buffer = io.BytesIO()
  now = datetime.now()
  fecha = now.strftime("%d/%m/%Y")
  validez = (now + timedelta(days=30)).strftime("%d/%m/%Y")

  doc = SimpleDocTemplate(
    buffer, pagesize=A4,
    leftMargin=14*mm, rightMargin=14*mm,
    topMargin=34*mm, bottomMargin=15*mm
  )

  tpl = BMCPageTemplate(doc_num, fecha, validez)
  story = []

  s_title = ParagraphStyle('T', fontSize=16, fontName='Helvetica-Bold',
                           textColor=NAVY, spaceAfter=4*mm, leading=18)
  s_sub = ParagraphStyle('S', fontSize=9, fontName='Helvetica',
                         textColor=STEEL, spaceAfter=3*mm)
  s_section = ParagraphStyle('Sec', fontSize=11, fontName='Helvetica-Bold',
                             textColor=STEEL, spaceBefore=3*mm, spaceAfter=1.5*mm)
  s_label = ParagraphStyle('L', fontSize=9, fontName='Helvetica-Bold', textColor=SLATE)
  s_value = ParagraphStyle('V', fontSize=9, fontName='Helvetica', textColor=SLATE)
  s_cell = ParagraphStyle('C', fontSize=8.5, fontName='Helvetica', textColor=SLATE)
  s_cell_b = ParagraphStyle('CB', fontSize=8.5, fontName='Helvetica-Bold', textColor=SLATE)
  s_cell_r = ParagraphStyle('CR', fontSize=8.5, fontName='Helvetica', textColor=SLATE, alignment=TA_RIGHT)
  s_cell_br = ParagraphStyle('CBR', fontSize=8.5, fontName='Helvetica-Bold', textColor=SLATE, alignment=TA_RIGHT)
  s_cell_c = ParagraphStyle('CC', fontSize=8.5, fontName='Helvetica', textColor=SLATE, alignment=TA_CENTER)
  s_hdr = ParagraphStyle('H', fontSize=8.5, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)
  s_hdr_r = ParagraphStyle('HR', fontSize=8.5, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_RIGHT)

  story.append(Paragraph("PRESUPUESTO", s_title))
  story.append(Paragraph(
    f"Nro. <b>{doc_num}</b>  ·  {fecha}  ·  Valido hasta <b>{validez}</b>", s_sub))

  cl = data.cliente
  client_rows = [
    [Paragraph("<b>Cliente</b>", s_label), Paragraph(cl.nombre, s_value),
     Paragraph("<b>Tel / WhatsApp</b>", s_label), Paragraph(cl.telefono, s_value)],
    [Paragraph("<b>Obra / Entrega</b>", s_label), Paragraph(cl.obra, s_value),
     Paragraph("<b>Direccion</b>", s_label), Paragraph(cl.direccion, s_value)],
  ]
  ct = Table(client_rows, colWidths=[26*mm, 55*mm, 28*mm, 55*mm])
  ct.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, -1), SKY),
    ('BOX', (0, 0), (-1, -1), 0.4, STEEL),
    ('INNERGRID', (0, 0), (-1, -1), 0.2, BORDER),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ('LEFTPADDING', (0, 0), (-1, -1), 5),
  ]))
  story.append(ct)
  story.append(Spacer(1, 3*mm))
  s_note = ParagraphStyle('N', fontSize=7, fontName='Helvetica', textColor=SLATE, leading=9, spaceAfter=0.5*mm)

  if data.spec:
    spec_vals = []
    spec_labels = []
    for label, val in data.spec.items():
      spec_vals.append(Paragraph(f"<b>{val}</b>",
                                 ParagraphStyle('SV', fontSize=11, fontName='Helvetica-Bold',
                                                textColor=NAVY, alignment=TA_CENTER)))
      spec_labels.append(Paragraph(label,
                                   ParagraphStyle('SL', fontSize=6.5, fontName='Helvetica',
                                                  textColor=HexColor("#666666"), alignment=TA_CENTER)))
      n = len(spec_vals)
      spec_t = Table([spec_vals, spec_labels], colWidths=[usable/n]*n)
      spec_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#F0F4F8")),
        ('BOX', (0, 0), (-1, -1), 0.3, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 1),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ]))
      story.append(spec_t)
      story.append(Spacer(1, 3*mm))

  story.append(Paragraph("Detalle de Materiales", s_section))

  hdr = [
    Paragraph("<b>Producto</b>", s_cell_b),
    Paragraph("<b>Largo</b>", s_hdr),
    Paragraph("<b>Cant.</b>", s_hdr),
    Paragraph("<b>Area m2</b>", s_hdr),
    Paragraph("<b>USD/m2</b>", s_hdr_r),
    Paragraph("<b>Total USD</b>", s_hdr_r),
  ]

  rows = [hdr]
  for item in data.items:
    rows.append([
      Paragraph(item.nombre, s_cell),
      Paragraph(f"{item.largo:.2f} m", s_cell_c),
      Paragraph(str(item.cantidad), s_cell_c),
      Paragraph(f"{item.area:.2f}", s_cell_c),
      Paragraph(f"{item.precio_m2:.2f}", s_cell_r),
      Paragraph(fmt(item.total), s_cell_br),
    ])

  col_w = [58*mm, 18*mm, 14*mm, 20*mm, 22*mm, 30*mm]
  tbl = Table(rows, colWidths=col_w)
  tbl_style = [
    ('BACKGROUND', (0, 0), (-1, 0), NAVY),
    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
    ('LINEBELOW', (0, 0), (-1, -1), 0.3, BORDER),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
  ]
  for i in range(1, len(rows)):
    if i % 2 == 0:
      tbl_style.append(('BACKGROUND', (0, i), (-1, i), HexColor("#F5F7FA")))
      tbl.setStyle(TableStyle(tbl_style))
      story.append(tbl)
      story.append(Spacer(1, 3*mm))

  if data.accesorios:
    story.append(Paragraph("Accesorios y Terminaciones", s_section))
    acc_hdr = [
      Paragraph("<b>Accesorio</b>", s_cell_b),
      Paragraph("<b>Largo</b>", s_hdr),
      Paragraph("<b>Cant.</b>", s_hdr),
      Paragraph("<b>USD/u</b>", s_hdr_r),
      Paragraph("<b>Total USD</b>", s_hdr_r),
    ]
    acc_rows = [acc_hdr]
    for a in data.accesorios:
      acc_rows.append([
        Paragraph(a.nombre, s_cell),
        Paragraph(f"{a.largo:.1f} m" if a.largo else "—", s_cell_c),
        Paragraph(str(a.cantidad), s_cell_c),
        Paragraph(f"{a.precio_unit:.2f}", s_cell_r),
        Paragraph(fmt(a.total), s_cell_br),
      ])
      acc_cw = [68*mm, 20*mm, 16*mm, 24*mm, 30*mm]
      acc_t = Table(acc_rows, colWidths=acc_cw)
      acc_style = list(tbl_style)
      acc_style[0] = ('BACKGROUND', (0, 0), (-1, 0), STEEL)
      acc_t.setStyle(TableStyle(acc_style))
      story.append(acc_t)
      story.append(Spacer(1, 3*mm))

  story.append(Spacer(1, 1*mm))
  fin = data.financials
  fin_rows = [
    ["", Paragraph("Subtotal (USD sin IVA)", s_cell), Paragraph(f"$ {fmt(fin.subtotal)}", s_cell_r)],
    ["", Paragraph("IVA 22%", s_cell), Paragraph(f"$ {fmt(fin.iva)}", s_cell_r)],
    ["", Paragraph("<b>Total Materiales (USD IVA incl.)</b>", s_cell_b),
     Paragraph(f"<b>$ {fmt(fin.total_mat)}</b>", s_cell_br)],
  ]
  if fin.envio:
    fin_rows.append(
      ["", Paragraph(f"Envio referencia ({fin.envio_nota or 'a coordinar'})", s_cell),
       Paragraph(f"$ {fmt(fin.envio)}", s_cell_r)]
    )

  fin_t = Table(fin_rows, colWidths=[usable - 95*mm, 58*mm, 37*mm])
  fin_t.setStyle(TableStyle([
    ('LINEABOVE', (1, 0), (-1, 0), 0.5, STEEL),
    ('LINEBELOW', (1, -1), (-1, -1), 0.5, STEEL),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ('BACKGROUND', (1, 2), (-1, 2), HexColor("#F0F4F8")),
  ]))
  story.append(fin_t)
  story.append(Spacer(1, 3*mm))

  total_val = fin.total_general

  total_label = Paragraph("TOTAL GENERAL",
                          ParagraphStyle('TL', fontSize=9, fontName='Helvetica', textColor=WHITE, alignment=TA_CENTER))
  total_amount = Paragraph(f"USD  $ {fmt(total_val)}",
                           ParagraphStyle('TA', fontSize=20, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER))

  total_box = Table([[total_label], [total_amount]], colWidths=[usable])
  total_box.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, -1), AMBER),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('TOPPADDING', (0, 0), (0, 0), 6),
    ('BOTTOMPADDING', (0, 0), (0, 0), 0),
    ('TOPPADDING', (0, 1), (0, 1), 2),
    ('BOTTOMPADDING', (0, 1), (0, 1), 8),
    ('ROUNDEDCORNERS', [4, 4, 4, 4]),
  ]))
  story.append(total_box)
  story.append(Spacer(1, 4*mm))

  story.append(Paragraph("Condiciones y Notas Tecnicas", s_section))

  conditions = data.condiciones if data.condiciones else DEFAULT_CONDITIONS
  conditions.append(
    f"<b>Validez:</b> 30 dias desde la emision ({fecha}). "
    "Precios y disponibilidad sujetos a cambios posteriores."
  )
  for c in conditions:
    story.append(Paragraph(f">  {c}", s_note))

  story.append(Spacer(1, 3*mm))

  story.append(Paragraph("Datos Bancarios para Transferencia", s_section))

  bank_rows = [
    [Paragraph("<b>Deposito Bancario</b>", s_label),
     Paragraph(f"Titular: <b>{BANK['titular']}</b>  --  RUT: <b>{BANK['rut']}</b>", s_value)],
    [Paragraph(f"<b>{BANK['tipo_cuenta']} - {BANK['banco']}</b>", s_label),
     Paragraph(f"Cuenta Dolares: <b>{BANK['cuenta_usd']}</b>", s_value)],
    [Paragraph(f"Consultas: <b>{BANK['consultas']}</b>", s_value),
     Paragraph("", s_value)],
  ]
  bank_t = Table(bank_rows, colWidths=[55*mm, usable - 55*mm])
  bank_t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, -1), HexColor("#FAFAF5")),
    ('BOX', (0, 0), (-1, -1), 0.4, BORDER),
    ('INNERGRID', (0, 0), (-1, -1), 0.2, BORDER),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ('LEFTPADDING', (0, 0), (-1, -1), 4),
  ]))

  cta_box = Table([[
    Paragraph(
      "Para confirmar este presupuesto, responda <b>CONFIRMO</b> por WhatsApp<br/>"
      "o envie este documento firmado a info@bmcuruguay.com.uy",
      ParagraphStyle('CTA', fontSize=9.5, fontName='Helvetica', textColor=NAVY,
                     alignment=TA_CENTER, leading=14))
  ]], colWidths=[usable])
  cta_box.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, -1), SKY),
    ('BOX', (0, 0), (-1, -1), 1, STEEL),
    ('TOPPADDING', (0, 0), (-1, -1), 8),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ('ROUNDEDCORNERS', [4, 4, 4, 4]),
  ]))
  story.append(cta_box)

  doc.build(story, onFirstPage=tpl, onLaterPages=tpl)
  pdf_bytes = buffer.getvalue()
  buffer.close()
  return pdf_bytes


router = APIRouter(tags=["Cotizaciones PDF"])


@router.post("/cotizaciones/generar_pdf", response_model=CotizacionResponse)
async def generar_pdf(data: CotizacionRequest, api_key: str = Depends(verify_api_key)):
    """Generate a professional BMC Uruguay quotation PDF and upload to Google Drive."""
    try:
        doc_num = generate_doc_number("BMC")
        logger.info(f"Generating PDF: {doc_num} for {data.cliente.nombre}")

        pdf_bytes = generate_pdf_bytes(data, doc_num)
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")

        now = datetime.now()
        folder_id = ensure_folder_structure(now.year, now.month)

        client_safe = sanitize_filename(data.cliente.nombre)
        filename = f"{doc_num}_{client_safe}.pdf"

        file_id, view_url, download_url = upload_pdf(pdf_bytes, filename, folder_id)
        drive_path = get_drive_path(now.year, now.month, filename)

        fecha = now.strftime("%d/%m/%Y")
        validez = (now + timedelta(days=30)).strftime("%d/%m/%Y")

        logger.info(f"PDF uploaded: {drive_path} -> {view_url}")

        return CotizacionResponse(
            success=True,
            doc_num=doc_num,
            pdf_url=view_url,
            pdf_download=download_url,
            drive_path=drive_path,
            total_usd=data.financials.total_general,
            fecha=fecha,
            validez=validez,
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@router.post("/cotizaciones/preview_pdf")
async def preview_pdf(data: CotizacionRequest, api_key: str = Depends(verify_api_key)):
    """Generate PDF and return it directly (no Drive upload). Useful for testing."""
    from fastapi.responses import Response

    try:
        doc_num = generate_doc_number("PRV")
        pdf_bytes = generate_pdf_bytes(data, doc_num)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{doc_num}_preview.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"PDF preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando preview: {str(e)}")
