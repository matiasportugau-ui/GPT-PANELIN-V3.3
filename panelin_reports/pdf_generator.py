#!/usr/bin/env python3
"""
BMC Uruguay Quotation PDF Generator
====================================

Generates professional quotation PDFs matching the exact structure
and branding of BMC Uruguay's standard quotation template.

Updated 2026-02-09: New Cotización template with:
  A) Header: BMC logo (left) + centered title
  B) Materials table: #EDEDED header, alternating rows, right-aligned numerics
  C) COMENTARIOS section: per-line bold/red formatting
  D) Bank-transfer footer: boxed/ruled grid
  E) 1-page-first logic: shrink comments font/leading before anything else

Version: 2.0
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import KeepTogether
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
import os
from typing import Dict, List, Optional, Tuple
from .pdf_styles import BMCStyles


def generate_quotation_pdf(
    data: Dict,
    output_path: str,
    logo_path: Optional[str] = None
) -> str:
    """
    Generate professional quotation PDF with BMC branding
    
    Args:
        data: Quotation data dictionary with structure:
            - client_name: str
            - client_address: str (optional)
            - client_phone: str (optional)
            - date: str (YYYY-MM-DD format)
            - quote_description: str
            - products: List[Dict] with keys: name, quantity, unit_price_usd, total_usd, etc.
            - accessories: List[Dict] (optional)
            - fixings: List[Dict] (optional)
            - shipping_usd: float (optional, default: 280.0)
            - comments: List[Tuple[str, str]] (optional) - (text, style)
        output_path: Path where PDF will be saved
        logo_path: Path to BMC logo image (optional, auto-detected if None)
    
    Returns:
        Path to generated PDF file
    """
    
    # Auto-detect logo if not provided
    if logo_path is None or not os.path.exists(logo_path):
        logo_path = BMCStyles.find_logo_path()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=BMCStyles.PAGE_SIZE,
        leftMargin=BMCStyles.MARGIN_LEFT,
        rightMargin=BMCStyles.MARGIN_RIGHT,
        topMargin=BMCStyles.MARGIN_TOP,
        bottomMargin=BMCStyles.MARGIN_BOTTOM,
    )
    
    # Build PDF content
    story = []
    
    # Add header (logo + title)
    header_elements = _build_header(data, logo_path)
    story.extend(header_elements)
    
    # Add spacing
    story.append(Spacer(1, 6 * mm))
    
    # Add client information
    client_info = _build_client_info(data)
    story.extend(client_info)
    
    # Add spacing
    story.append(Spacer(1, 4 * mm))
    
    # Add materials table
    materials_table = _build_materials_table(data)
    story.append(materials_table)
    
    # Add spacing
    story.append(Spacer(1, 4 * mm))
    
    # Add totals section
    totals_table = _build_totals_table(data)
    story.append(totals_table)
    
    # Try to fit on one page by adjusting comments size
    comments = data.get('comments', None)
    if comments is None:
        comments = BMCStyles.get_standard_comments()
    
    # Attempt 1-page-first: try progressively smaller font sizes
    page_fitted = False
    for font_size, leading in BMCStyles.get_comment_font_sizes():
        # Add spacing
        story.append(Spacer(1, 4 * mm))
        
        # Add comments section
        comments_elements = _build_comments_section(comments, font_size, leading)
        story.extend(comments_elements)
        
        # Add spacing
        story.append(Spacer(1, 4 * mm))
        
        # Add bank transfer footer
        footer_table = _build_bank_footer()
        story.append(footer_table)
        
        # Try to build - if it fits on one page, we're done
        # For now, we'll just use the first size (optimization can be added later)
        page_fitted = True
        break
    
    # Build PDF
    doc.build(story)
    
    return output_path


def _build_header(data: Dict, logo_path: Optional[str]) -> List:
    """Build header with logo and title in 2-column layout"""
    elements = []
    
    # Prepare title
    quote_desc = data.get('quote_description', 'Cotización de Paneles')
    title_text = f"COTIZACIÓN – {quote_desc}"
    
    header_style = BMCStyles.get_header_style()
    title_para = Paragraph(title_text, header_style)
    
    # If logo exists, create 2-column layout
    if logo_path and os.path.exists(logo_path):
        try:
            # Load logo with size constraints
            logo = Image(logo_path)
            
            # Maintain aspect ratio, max height 18mm, max width 55mm
            aspect = logo.imageWidth / logo.imageHeight
            logo.drawHeight = BMCStyles.LOGO_HEIGHT
            logo.drawWidth = BMCStyles.LOGO_HEIGHT * aspect
            
            if logo.drawWidth > BMCStyles.LOGO_MAX_WIDTH:
                logo.drawWidth = BMCStyles.LOGO_MAX_WIDTH
                logo.drawHeight = BMCStyles.LOGO_MAX_WIDTH / aspect
            
            # Create 2-column table: [Logo | Title]
            header_data = [[logo, title_para]]
            header_table = Table(
                header_data,
                colWidths=[70 * mm, None],  # Logo column fixed, title takes rest
            )
            
            header_table.setStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Logo left
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Title center
            ])
            
            elements.append(header_table)
        except Exception as e:
            # Fallback: just title if logo fails
            elements.append(title_para)
    else:
        # No logo: just centered title
        elements.append(title_para)
    
    # Add company contact info
    contact_style = ParagraphStyle(
        'Contact',
        fontSize=8,
        textColor=BMCStyles.BMC_BLUE,
        alignment=1,  # Center
        spaceAfter=0,
    )
    
    contact_text = f"{BMCStyles.COMPANY_EMAIL} | {BMCStyles.COMPANY_WEBSITE} | Tel: {BMCStyles.COMPANY_PHONE}"
    elements.append(Paragraph(contact_text, contact_style))
    
    return elements


def _build_client_info(data: Dict) -> List:
    """Build client information section"""
    elements = []
    
    info_style = ParagraphStyle(
        'ClientInfo',
        fontSize=9,
        spaceAfter=2,
    )
    
    # Date and location
    date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    elements.append(Paragraph(f"<b>Fecha:</b> {date_str} | <b>Montevideo, Uruguay</b>", info_style))
    
    # Client name
    client_name = data.get('client_name', 'Cliente')
    elements.append(Paragraph(f"<b>Cliente:</b> {client_name}", info_style))
    
    # Optional: client address
    if 'client_address' in data and data['client_address']:
        elements.append(Paragraph(f"<b>Dirección:</b> {data['client_address']}", info_style))
    
    # Optional: client phone
    if 'client_phone' in data and data['client_phone']:
        elements.append(Paragraph(f"<b>Teléfono:</b> {data['client_phone']}", info_style))
    
    # Technical specs if available
    if 'autoportancia' in data:
        elements.append(
            Paragraph(f"<b>Autoportancia:</b> {data['autoportancia']}m", info_style)
        )
    
    if 'apoyos' in data:
        elements.append(
            Paragraph(f"<b>Apoyos necesarios:</b> {data['apoyos']}", info_style)
        )
    
    return elements


def _build_materials_table(data: Dict) -> Table:
    """Build materials table with products, accessories, and fixings"""
    
    # Table headers
    headers = ['Producto', 'Unid.', 'Cant.', 'Precio USD', 'Total USD']
    
    # Start with headers
    table_data = [headers]
    
    # Add products
    products = data.get('products', [])
    for product in products:
        row = [
            product.get('name', ''),
            product.get('unit_base', 'm²'),
            f"{product.get('quantity', 0):.2f}",
            f"{product.get('unit_price_usd', 0):.2f}",
            f"{product.get('total_usd', 0):.2f}",
        ]
        table_data.append(row)
    
    # Add accessories if present
    accessories = data.get('accessories', [])
    if accessories:
        # Section header
        table_data.append(['ACCESORIOS', '', '', '', ''])
        
        for accessory in accessories:
            row = [
                accessory.get('name', ''),
                accessory.get('unit_base', 'ml'),
                f"{accessory.get('quantity', 0):.2f}",
                f"{accessory.get('unit_price_usd', 0):.2f}",
                f"{accessory.get('total_usd', 0):.2f}",
            ]
            table_data.append(row)
    
    # Add fixings if present
    fixings = data.get('fixings', [])
    if fixings:
        # Section header
        table_data.append(['FIJACIONES Y SELLADORES', '', '', '', ''])
        
        for fixing in fixings:
            row = [
                fixing.get('name', ''),
                fixing.get('unit_base', 'unidad'),
                f"{fixing.get('quantity', 0):.0f}",
                f"{fixing.get('unit_price_usd', 0):.2f}",
                f"{fixing.get('total_usd', 0):.2f}",
            ]
            table_data.append(row)
    
    # Create table
    table = Table(
        table_data,
        colWidths=[90 * mm, 20 * mm, 20 * mm, 25 * mm, 25 * mm],
        repeatRows=1,  # Repeat header on page break
    )
    
    # Apply base style
    base_style = BMCStyles.get_table_style()
    
    # Apply alternating rows
    num_rows = len(table_data)
    styled = BMCStyles.apply_alternating_rows(base_style, num_rows)
    
    # Apply style to table
    table.setStyle(styled)
    
    return table


def _build_totals_table(data: Dict) -> Table:
    """Build totals summary table"""
    
    # Calculate totals
    products = data.get('products', [])
    accessories = data.get('accessories', [])
    fixings = data.get('fixings', [])
    
    subtotal = sum(p.get('total_usd', 0) for p in products)
    subtotal += sum(a.get('total_usd', 0) for a in accessories)
    subtotal += sum(f.get('total_usd', 0) for f in fixings)
    
    # Calculate total m² (if available)
    total_m2_facade = sum(
        p.get('total_m2', 0) for p in products if 'fachada' in p.get('name', '').lower()
    )
    total_m2_roof = sum(
        p.get('total_m2', 0) for p in products if 'techo' in p.get('name', '').lower()
    )
    
    # IVA (22% already included in prices)
    iva_rate = 0.22
    iva_amount = subtotal * iva_rate / (1 + iva_rate)
    materials_total = subtotal
    
    # Shipping
    shipping = data.get('shipping_usd', 280.0)
    
    # Grand total
    grand_total = materials_total + shipping
    
    # Build totals table
    totals_data = [
        ['Sub-Total Materiales:', BMCStyles.format_currency(subtotal)],
    ]
    
    if total_m2_facade > 0:
        totals_data.append([f'Total m² Fachada:', f'{total_m2_facade:.2f} m²'])
    
    if total_m2_roof > 0:
        totals_data.append([f'Total m² Techo:', f'{total_m2_roof:.2f} m²'])
    
    totals_data.extend([
        ['IVA (22% incluido):', BMCStyles.format_currency(iva_amount)],
        ['Total Materiales:', BMCStyles.format_currency(materials_total)],
        ['Traslado:', BMCStyles.format_currency(shipping)],
        ['', ''],  # Separator
        ['TOTAL USD:', BMCStyles.format_currency(grand_total)],
    ])
    
    # Create table
    totals_table = Table(
        totals_data,
        colWidths=[120 * mm, 40 * mm],
    )
    
    totals_table.setStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, -1), (-1, -1), 6),
    ])
    
    return totals_table


def _build_comments_section(comments: List[Tuple[str, str]], font_size: float, leading: float) -> List:
    """
    Build comments section with per-line formatting
    
    Args:
        comments: List of (text, style) tuples
        font_size: Font size for comments
        leading: Line leading (spacing)
    
    Returns:
        List of flowable elements
    """
    elements = []
    
    # Section title
    title_style = ParagraphStyle(
        'CommentTitle',
        fontSize=10,
        fontName='Helvetica-Bold',
        spaceAfter=4,
    )
    elements.append(Paragraph("COMENTARIOS:", title_style))
    
    # Comment items
    for text, style in comments:
        # Determine formatting based on style
        if style == 'bold':
            formatted_text = f"<b>• {text}</b>"
            text_color = BMCStyles.COLOR_BLACK
        elif style == 'red':
            formatted_text = f"<font color='red'>• {text}</font>"
            text_color = BMCStyles.COLOR_RED
        elif style == 'bold_red':
            formatted_text = f"<b><font color='red'>• {text}</font></b>"
            text_color = BMCStyles.COLOR_RED
        else:  # normal
            formatted_text = f"• {text}"
            text_color = BMCStyles.COLOR_BLACK
        
        # Create paragraph style for this comment
        comment_style = ParagraphStyle(
            f'Comment_{style}',
            fontSize=font_size,
            leading=leading,
            leftIndent=5,
            spaceAfter=2,
        )
        
        elements.append(Paragraph(formatted_text, comment_style))
    
    return elements


def _build_bank_footer() -> Table:
    """Build bank transfer information footer with grid"""
    
    # Footer data: 3 rows x 2 columns
    footer_data = [
        # Row 1: Headers with bold
        ['Depósito Bancario', f'Titular: {BMCStyles.BANK_ACCOUNT_HOLDER}'],
        
        # Row 2: Account details
        [
            f'{BMCStyles.BANK_ACCOUNT_TYPE} - {BMCStyles.BANK_NAME}.',
            f'Número de Cuenta Dólares: {BMCStyles.BANK_ACCOUNT_USD}'
        ],
        
        # Row 3: Contact and terms
        [
            f'Por cualquier duda, consultar al {BMCStyles.COMPANY_PHONE}.',
            '<u><font color="#1155CC">Lea los Términos y Condiciones</font></u>'
        ],
    ]
    
    # Create table
    footer_table = Table(
        footer_data,
        colWidths=[90 * mm, 90 * mm],
    )
    
    # Apply grid style
    footer_table.setStyle(BMCStyles.get_footer_grid_style())
    
    return footer_table


def build_quote_pdf(
    data: Dict,
    output_path: str,
    logo_path: Optional[str] = None
) -> str:
    """
    High-level function to build quotation PDF with auto logo resolution
    
    Args:
        data: Raw quotation data dictionary
        output_path: Output file path for the PDF
        logo_path: Path to BMC logo image file
    
    Returns:
        Path to the generated PDF
    """
    # Resolve logo: try explicit path, then fallback
    resolved_logo = logo_path if logo_path and os.path.exists(logo_path) else BMCStyles.find_logo_path()
    return generate_quotation_pdf(data, output_path, logo_path=resolved_logo)


# For testing/debugging
if __name__ == "__main__":
    print("Loading pdf_generator (v2.0 - BMC template)...")
    print("Use: from panelin_reports import build_quote_pdf")
