"""
Panelin Agno — Quotation Service
==================================

Capa de servicio que encapsula el motor de cotizaciones v4.0.
El engine panelin_v4/ es dominio puro y NO se modifica aquí.

Esta capa:
  - Provee interfaces limpias para el agente Agno
  - Serializa / deserializa resultados
  - Registra trazas de ejecución
  - Centraliza acceso al pipeline determinístico
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy imports del engine (no modificar panelin_v4/)
def _get_engine():
    from panelin_v4.engine.quotation_engine import process_quotation, process_batch
    from panelin_v4.engine.classifier import OperatingMode
    return process_quotation, process_batch, OperatingMode


@dataclass
class QuotationRequest:
    """Request de cotización normalizado para el servicio."""
    text: str
    mode: Optional[str] = None          # informativo | pre_cotizacion | formal
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_location: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class QuotationServiceResult:
    """Resultado del servicio de cotizaciones."""
    success: bool
    quote_id: Optional[str]
    mode: str
    status: str
    level: str
    confidence_score: float
    processing_ms: float
    data: dict                          # QuotationOutput serializado
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "quote_id": self.quote_id,
            "mode": self.mode,
            "status": self.status,
            "level": self.level,
            "confidence_score": self.confidence_score,
            "processing_ms": round(self.processing_ms, 2),
            "data": self.data,
            "error": self.error,
        }

    def to_summary(self) -> str:
        """Resumen conciso para el agente LLM."""
        if not self.success:
            return f"Error en cotización: {self.error}"

        d = self.data
        pricing = d.get("pricing", {})
        bom = d.get("bom", {})

        total = pricing.get("subtotal_total_usd", 0)
        panels = bom.get("panel_count", 0)
        area = bom.get("area_m2", 0)

        lines = [
            f"Cotización {self.quote_id} | Estado: {self.status.upper()}",
            f"Modo: {self.mode} | Nivel SRE: {self.level} | Confianza: {self.confidence_score:.0f}/100",
            f"Área: {area:.1f} m² | Paneles: {panels} unid",
            f"Total estimado: USD {total:,.2f} (IVA incluido)",
        ]

        missing = pricing.get("missing_prices", [])
        if missing:
            lines.append(f"⚠ Precios no encontrados: {', '.join(missing)}")

        warnings = d.get("validation", {}).get("warnings", [])[:3]
        if warnings:
            lines.append("Advertencias: " + "; ".join(warnings))

        assumptions = d.get("assumptions_used", [])
        if assumptions:
            lines.append(f"Supuestos aplicados: {'; '.join(assumptions)}")

        return "\n".join(lines)


class QuotationService:
    """Servicio principal de cotizaciones Panelin v4.0."""

    def __init__(self) -> None:
        self._engine_loaded = False

    def _ensure_engine(self):
        if not self._engine_loaded:
            global _process_quotation, _process_batch, _OperatingMode
            _process_quotation, _process_batch, _OperatingMode = _get_engine()
            self._engine_loaded = True

    def calculate(self, request: QuotationRequest) -> QuotationServiceResult:
        """Ejecuta el pipeline completo v4.0 de forma síncrona.

        El pipeline es 100% determinístico — sin LLM. < 0.4ms por cotización.
        """
        self._ensure_engine()
        t0 = time.perf_counter()

        try:
            force_mode = None
            if request.mode:
                try:
                    force_mode = _OperatingMode(request.mode)
                except ValueError:
                    logger.warning(f"Modo desconocido '{request.mode}', usando auto-detección")

            output = _process_quotation(
                text=request.text,
                force_mode=force_mode,
                client_name=request.client_name,
                client_phone=request.client_phone,
                client_location=request.client_location,
            )

            elapsed_ms = (time.perf_counter() - t0) * 1000

            return QuotationServiceResult(
                success=True,
                quote_id=output.quote_id,
                mode=output.mode,
                status=output.status,
                level=output.level,
                confidence_score=output.confidence_score,
                processing_ms=elapsed_ms,
                data=output.to_dict(),
            )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.exception(f"Error en pipeline de cotización: {exc}")
            return QuotationServiceResult(
                success=False,
                quote_id=None,
                mode=request.mode or "unknown",
                status="error",
                level="unknown",
                confidence_score=0.0,
                processing_ms=elapsed_ms,
                data={},
                error=str(exc),
            )

    def calculate_batch(
        self,
        requests: list[QuotationRequest],
        mode: Optional[str] = None,
    ) -> list[QuotationServiceResult]:
        """Procesa múltiples cotizaciones en batch."""
        self._ensure_engine()

        batch_dicts = [
            {
                "text": r.text,
                "client_name": r.client_name,
                "client_phone": r.client_phone,
                "client_location": r.client_location,
            }
            for r in requests
        ]

        force_mode = None
        if mode:
            try:
                force_mode = _OperatingMode(mode)
            except ValueError:
                pass

        outputs = _process_batch(batch_dicts, force_mode=force_mode)

        results = []
        for i, output in enumerate(outputs):
            req = requests[i]
            results.append(QuotationServiceResult(
                success=True,
                quote_id=output.quote_id,
                mode=output.mode,
                status=output.status,
                level=output.level,
                confidence_score=output.confidence_score,
                processing_ms=0.0,
                data=output.to_dict(),
            ))

        return results

    def search_products(self, query: str) -> list[dict]:
        """Búsqueda de productos en el catálogo (sin LLM)."""
        from src.core.config import get_settings
        import json

        settings = get_settings()
        results = []

        query_upper = query.upper()
        keywords = query_upper.split()

        for catalog_path in [settings.pricing_master_path, settings.accessories_catalog_path]:
            if not catalog_path.exists():
                continue
            with open(catalog_path, encoding="utf-8") as f:
                data = json.load(f)

            items = data if isinstance(data, list) else data.get("accesorios", [])
            if isinstance(data, dict) and not isinstance(items, list):
                items = []
                for v in data.values():
                    if isinstance(v, list):
                        items.extend(v)

            for item in items:
                if not isinstance(item, dict):
                    continue
                item_str = json.dumps(item, ensure_ascii=False).upper()
                if any(kw in item_str for kw in keywords):
                    results.append(item)
                    if len(results) >= 20:
                        break

            if len(results) >= 20:
                break

        return results


# Singleton del servicio
_service_instance: Optional[QuotationService] = None


def get_quotation_service() -> QuotationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = QuotationService()
    return _service_instance
