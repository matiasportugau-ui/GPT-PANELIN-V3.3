"""
BMC Uruguay PDF Styles and Branding
====================================

Centralized style definitions for BMC Uruguay quotation PDFs.
Ensures consistent branding and layout across all generated documents.

Updated 2026-02-09: New BMC Cotización template with
  - 2-column header (logo + title)
  - Table styling: #EDEDED header, alternating #FAFAFA rows, right-aligned numerics
  - COMENTARIOS section with per-line bold/red formatting
  - Bank-transfer footer boxed grid

Version: 2.0
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import TableStyle
import os


class BMCStyles:
    """BMC Uruguay brand styling constants and helper methods"""
    
    # Brand Colors
    BMC_BLUE = colors.HexColor("#003366")  # Primary brand color
    BMC_LINK_BLUE = colors.HexColor("#1155CC")  # For links
    
    # Table Colors
    TABLE_HEADER_BG = colors.HexColor("#EDEDED")  # Light gray header
    TABLE_ALT_ROW_BG = colors.HexColor("#FAFAFA")  # Very light gray alternating rows
    TABLE_GRID_COLOR = colors.HexColor("#D0D0D0")  # Grid lines
    TABLE_HEADER_LINE = colors.HexColor("#CCCCCC")  # Header bottom line
    
    # Standard Colors
    COLOR_BLACK = colors.black
    COLOR_RED = colors.red
    
    # Page Settings
    PAGE_SIZE = A4
    PAGE_WIDTH, PAGE_HEIGHT = A4
    
    # Margins (in mm, converted to points)
    MARGIN_LEFT = 12 * mm
    MARGIN_RIGHT = 12 * mm
    MARGIN_TOP = 10 * mm
    MARGIN_BOTTOM = 9 * mm
    
    # Logo Settings
    LOGO_HEIGHT = 18 * mm
    LOGO_MAX_WIDTH = 55 * mm
    
    # Font Sizes (in points)
    FONT_TITLE = 14
    FONT_TABLE_HEADER = 9.1
    FONT_TABLE_BODY = 8.6
    FONT_COMMENTS_BASE = 8.1
    FONT_COMMENTS_MIN = 6.8
    FONT_FOOTER = 8.4
    
    # Line Heights (leading)
    LEADING_COMMENTS_BASE = 9.5
    LEADING_COMMENTS_MIN = 7.8
    
    # Company Information
    COMPANY_NAME = "BMC Uruguay"
    COMPANY_EMAIL = "info@bmcuruguay.com.uy"
    COMPANY_WEBSITE = "www.bmcuruguay.com.uy"
    COMPANY_PHONE = "092 663 245"
    
    # Bank Information
    BANK_ACCOUNT_HOLDER = "Metalog SAS – RUT: 120403630012"
    BANK_NAME = "BROU"
    BANK_ACCOUNT_TYPE = "Caja de Ahorro"
    BANK_ACCOUNT_USD = "110520638-00002"
    
    @classmethod
    def get_header_style(cls):
        """Returns style for the PDF header/title"""
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'BMCHeader',
            parent=styles['Heading1'],
            fontSize=cls.FONT_TITLE,
            textColor=cls.BMC_BLUE,
            fontName='Helvetica-Bold',
            alignment=1,  # Center
            spaceAfter=6,
        )
    
    @classmethod
    def get_table_style(cls):
        """
        Returns TableStyle for materials table with BMC branding
        
        Features:
        - Light gray header (#EDEDED)
        - Alternating white/#FAFAFA rows
        - Right-aligned numeric columns
        - Thin grid lines
        """
        return TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), cls.TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), cls.COLOR_BLACK),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), cls.FONT_TABLE_HEADER),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2.5),
            ('TOPPADDING', (0, 0), (-1, 0), 2.5),
            
            # Header bottom line (thicker)
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, cls.TABLE_HEADER_LINE),
            
            # Body rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), cls.FONT_TABLE_BODY),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2.5),
            ('TOPPADDING', (0, 1), (-1, -1), 2.5),
            
            # First column (product name) - left aligned
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # All other columns (numeric) - right aligned
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            
            # Grid lines
            ('GRID', (0, 0), (-1, -1), 0.4, cls.TABLE_GRID_COLOR),
            
            # Valign
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    
    @classmethod
    def apply_alternating_rows(cls, table_style, num_rows):
        """
        Applies alternating row background colors to a table style
        
        Args:
            table_style: TableStyle object to modify
            num_rows: Total number of rows (including header)
        """
        # Start from row 1 (skip header row 0)
        for i in range(1, num_rows):
            if i % 2 == 0:  # Even rows (2, 4, 6, ...) get light gray
                table_style.add('BACKGROUND', (0, i), (-1, i), cls.TABLE_ALT_ROW_BG)
            # Odd rows remain white (no need to set)
        
        return table_style
    
    @classmethod
    def get_footer_grid_style(cls):
        """Returns TableStyle for bank transfer footer grid"""
        return TableStyle([
            # Outer border (thicker)
            ('BOX', (0, 0), (-1, -1), 1.0, cls.COLOR_BLACK),
            
            # Inner grid lines
            ('INNERGRID', (0, 0), (-1, -1), 0.5, cls.TABLE_GRID_COLOR),
            
            # Header row (first row) with gray background
            ('BACKGROUND', (0, 0), (-1, 0), cls.TABLE_HEADER_BG),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            
            # All rows
            ('FONTSIZE', (0, 0), (-1, -1), cls.FONT_FOOTER),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
    
    @classmethod
    def get_standard_comments(cls):
        """
        Returns list of standard quotation comments with formatting rules
        
        Format: [(text, style), ...]
        where style is: 'normal', 'bold', 'red', or 'bold_red'
        """
        return [
            (
                "Entrega de 10 a 15 días, dependemos de producción.",
                "bold",
            ),
            (
                "Oferta válida por 10 días a partir de la fecha.",
                "red",
            ),
            (
                "Incluye descuentos de Pago al Contado. Seña del 60% al hacer el pedido.",
                "bold_red",
            ),
            (
                "El Saldo a la entrega o 48 horas antes de cargar para coordinar.",
                "normal",
            ),
            (
                "Puede ver video de montaje en: www.youtube.com/@bmcpanelesmetalicosuruguay6160",
                "normal",
            ),
            (
                "No incluye descarga del material. Se requieren 2 personas.",
                "normal",
            ),
        ]
    
    @classmethod
    def get_standard_conditions(cls):
        """Returns list of standard quotation conditions"""
        return [
            "Precios en dólares americanos (USD)",
            "IVA incluido (22%)",
            "Validez de la oferta: 10 días",
            "Plazo de entrega: 10-15 días hábiles",
            "Forma de pago: 60% anticipo, 40% contra entrega",
            "Incluye traslado a Montevideo y área metropolitana",
            "Producto sujeto a disponibilidad de stock",
        ]
    
    @classmethod
    def find_logo_path(cls):
        """
        Searches for BMC logo in standard locations
        
        Returns:
            Path to logo file, or None if not found
        """
        possible_paths = [
            "/mnt/data/Logo_BMC- PNG.png",
            "panelin_reports/assets/bmc_logo.png",
            "assets/bmc_logo.png",
            "bmc_logo.png",
            "../bmc_logo.png",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    @classmethod
    def format_currency(cls, amount, currency="USD"):
        """
        Formats currency amount for display
        
        Args:
            amount: Numeric amount
            currency: Currency code (default: USD)
        
        Returns:
            Formatted string (e.g., "$1,234.56")
        """
        if currency == "USD":
            return f"${amount:,.2f}"
        else:
            return f"{currency} {amount:,.2f}"
    
    @classmethod
    def get_comment_font_sizes(cls):
        """
        Returns list of progressively smaller font sizes for comments
        Used for 1-page-first optimization
        
        Returns:
            List of (font_size, leading) tuples
        """
        return [
            (8.1, 9.5),   # Default
            (7.6, 8.8),   # Slightly smaller
            (7.2, 8.3),   # Smaller
            (6.8, 7.8),   # Minimum
        ]
