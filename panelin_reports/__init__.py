"""
Panelin Reports - Professional PDF Generation for BMC Uruguay
==============================================================

Version: 2.0 (Template v2.0 - 2026-02-09)

This package provides professional PDF quotation generation for BMC Uruguay
panel products with enhanced branding and styling.

Main Features:
- Professional BMC logo header (2-column layout)
- Styled tables with alternating row colors (#EDEDED header, #FAFAFA rows)
- Right-aligned numeric columns
- Formatted comments section (bold/red formatting per line)
- Bank transfer footer with grid/borders
- 1-page optimization (shrinks comments before other content)

Usage:
    from panelin_reports import build_quote_pdf
    
    pdf_path = build_quote_pdf(
        data=quotation_data,
        output_path="cotizacion_cliente.pdf",
        logo_path="/path/to/logo.png"
    )
"""

from .pdf_generator import generate_quotation_pdf, build_quote_pdf
from .pdf_styles import BMCStyles

__version__ = "2.0"
__all__ = ["generate_quotation_pdf", "build_quote_pdf", "BMCStyles"]
