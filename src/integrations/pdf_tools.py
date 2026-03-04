"""
Panelin v5.0 - PDF Generation Tools
=====================================

Wraps panelin_reports/ PDF generation as an Agno tool.
Generates professional quotation PDFs and optionally uploads to Google Drive.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from agno.tools import Toolkit


class PDFTools(Toolkit):
    """Agno toolkit for PDF quotation generation."""

    def __init__(self, output_dir: str = "panelin_reports/output"):
        super().__init__(name="panelin_pdf")
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.register(self.generar_pdf_cotizacion)

    def generar_pdf_cotizacion(
        self,
        cotizacion_json: str,
        nombre_cliente: str = "",
        incluir_bom_detallado: bool = True,
    ) -> str:
        """Genera un PDF profesional de cotización a partir del resultado del pipeline.

        Args:
            cotizacion_json: JSON string con el output completo de la cotización
                             (resultado de la herramienta `cotizar`).
            nombre_cliente: Nombre del cliente para el encabezado del PDF.
            incluir_bom_detallado: Si True, incluye tabla detallada de BOM.

        Returns:
            JSON con la ruta del PDF generado y metadata.
        """
        try:
            data = json.loads(cotizacion_json)
        except json.JSONDecodeError:
            return json.dumps({
                "error": True,
                "mensaje": "El JSON de cotización no es válido",
            }, ensure_ascii=False)

        quote_id = data.get("quote_id", "PV5-UNKNOWN")
        filename = f"{quote_id}.pdf"
        filepath = os.path.join(self._output_dir, filename)

        try:
            from panelin_reports.pdf_generator import generate_quotation_pdf
            generate_quotation_pdf(
                data=data,
                output_path=filepath,
                client_name=nombre_cliente,
                include_bom_detail=incluir_bom_detallado,
            )
            return json.dumps({
                "generado": True,
                "archivo": filepath,
                "filename": filename,
                "quote_id": quote_id,
            }, ensure_ascii=False)
        except ImportError:
            return json.dumps({
                "error": True,
                "mensaje": "Módulo panelin_reports no disponible. Instale reportlab.",
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": True,
                "mensaje": f"Error generando PDF: {str(e)}",
            }, ensure_ascii=False)
