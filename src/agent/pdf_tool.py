"""
src/agent/pdf_tool.py — PDF Generation como Agno Tool

Wrappea el módulo panelin_reports/ como una tool del agente.
El agente puede generar un PDF de cotización formal y obtener su URL.

Opcional: sube el PDF a Google Drive si las credenciales están configuradas.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)


def generar_pdf_cotizacion(
    quote_id: str,
    quote_json: str,
    nombre_cliente: str = "Cliente",
    guardar_en_drive: bool = False,
) -> str:
    """Genera un PDF profesional de cotización y retorna la ruta del archivo.

    Usa el engine ReportLab de panelin_reports/ para generar el PDF.
    Opcionalmente sube a Google Drive si las credenciales están configuradas.

    Args:
        quote_id: ID de la cotización (ej: PV4-20260304-ABCD1234).
        quote_json: JSON completo de la cotización (output de calcular_cotizacion).
        nombre_cliente: Nombre del cliente para el encabezado del PDF.
        guardar_en_drive: Si True, intenta subir a Google Drive.

    Returns:
        JSON con {ok, pdf_path, drive_url (si aplica), error (si falla)}.
    """
    try:
        quote_data = json.loads(quote_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return json.dumps({"ok": False, "error": f"JSON inválido: {exc}"})

    output_dir = settings.pdf_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{quote_id}.pdf"

    try:
        from panelin_reports.pdf_generator import generate_quotation_pdf

        generate_quotation_pdf(
            quote_data=quote_data.get("quote", quote_data),
            output_path=str(pdf_path),
            client_name=nombre_cliente,
        )

        result: dict = {
            "ok": True,
            "quote_id": quote_id,
            "pdf_path": str(pdf_path),
            "pdf_filename": pdf_path.name,
        }

        if guardar_en_drive:
            drive_url = _upload_to_drive(pdf_path, quote_id)
            if drive_url:
                result["drive_url"] = drive_url

        return json.dumps(result, ensure_ascii=False)

    except ImportError:
        logger.warning("panelin_reports no disponible — PDF no generado")
        return json.dumps({
            "ok": False,
            "error": "Módulo de PDF no disponible en este entorno",
        })
    except Exception as exc:
        logger.error("Error generando PDF %s: %s", quote_id, exc, exc_info=True)
        return json.dumps({"ok": False, "error": str(exc)})


def _upload_to_drive(pdf_path: Path, quote_id: str) -> Optional[str]:
    """Sube el PDF a Google Drive si las credenciales están disponibles."""
    try:
        from wolf_api.drive_uploader import upload_file

        url = upload_file(str(pdf_path), f"Cotizacion_{quote_id}.pdf")
        logger.info("PDF subido a Drive: %s", url)
        return url
    except Exception as exc:
        logger.warning("Error subiendo a Drive (no crítico): %s", exc)
        return None


PDF_TOOLS = [generar_pdf_cotizacion]
