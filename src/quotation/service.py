"""
src/quotation/service.py — QuotationService

Wrapper de dominio sobre el engine panelin_v4.
El engine v4 NO se modifica — este módulo adapta su interfaz al resto del stack.

Responsabilidades:
  - Ejecutar el pipeline determinístico (classify → parse → SRE → BOM → pricing → validate)
  - Generar quote_id único
  - Serializar resultados a dict
  - NUNCA inventar precios — toda la lógica viene del engine
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from panelin_v4.engine.classifier import OperatingMode, classify_request
from panelin_v4.engine.quotation_engine import QuotationOutput, process_quotation
from panelin_v4.evaluator.sai_engine import SAIResult, calculate_sai

logger = logging.getLogger(__name__)


@dataclass
class QuotationRequest:
    """Input para el servicio de cotización."""
    text: str
    mode: str = "pre_cotizacion"
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_location: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class QuotationServiceResult:
    """Resultado completo del pipeline de cotización."""
    output: QuotationOutput
    sai: SAIResult
    quote_dict: dict
    sai_dict: dict

    @property
    def quote_id(self) -> str:
        return self.output.quote_id

    @property
    def status(self) -> str:
        return self.output.status

    @property
    def mode(self) -> str:
        return self.output.mode

    @property
    def has_pricing(self) -> bool:
        pricing = self.quote_dict.get("pricing", {})
        return bool(pricing.get("subtotal_total_usd", 0) > 0)

    @property
    def is_blockable(self) -> bool:
        return self.output.status == "blocked"

    def to_dict(self) -> dict:
        return {
            "quote": self.quote_dict,
            "sai": self.sai_dict,
        }


_MODE_MAP: dict[str, OperatingMode] = {
    "informativo": OperatingMode.INFORMATIVO,
    "pre_cotizacion": OperatingMode.PRE_COTIZACION,
    "formal": OperatingMode.FORMAL,
}


class QuotationService:
    """Servicio de cotización — orquesta el engine v4.

    Diseñado para ser usado por:
      - Agno Workflow Steps (función pura, sin LLM)
      - API endpoints legacy (app.py)
      - Tests de integración
    """

    def run(self, request: QuotationRequest) -> QuotationServiceResult:
        """Ejecuta el pipeline completo de cotización.

        Este método es síncrono y puro — sin I/O externo, sin LLM.
        Latencia típica: < 0.5ms

        Args:
            request: QuotationRequest con texto y metadata del cliente.

        Returns:
            QuotationServiceResult con output completo + SAI score.
        """
        mode_key = (request.mode or "pre_cotizacion").strip().lower()
        force_mode = _MODE_MAP.get(mode_key, OperatingMode.PRE_COTIZACION)

        logger.debug(
            "Procesando cotización: mode=%s, text_len=%d, session=%s",
            force_mode.value, len(request.text), request.session_id,
        )

        output = process_quotation(
            text=request.text,
            force_mode=force_mode,
            client_name=request.client_name,
            client_phone=request.client_phone,
            client_location=request.client_location,
        )

        sai = calculate_sai(output)

        result = QuotationServiceResult(
            output=output,
            sai=sai,
            quote_dict=output.to_dict(),
            sai_dict=sai.to_dict(),
        )

        logger.info(
            "Cotización completada: id=%s status=%s sai=%.1f mode=%s",
            output.quote_id, output.status, sai.score, output.mode,
        )

        return result

    def classify_only(self, text: str) -> dict:
        """Solo clasifica el texto — usa para routing sin procesar."""
        classification = classify_request(text)
        return classification.to_dict()


# Singleton para reusar en toda la aplicación
quotation_service = QuotationService()
