"""
Panelin Agno — QuotationService
================================

Capa de servicio que envuelve el motor determinístico panelin_v4.
El engine NO se modifica — este módulo adapta su interfaz para el workflow Agno.

El engine v4 ejecuta las 9 etapas en < 0.4ms por cotización:
    text → classify → parse → SRE → BOM → pricing → validate → SAI → output
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from panelin_v4.engine.classifier import classify_request, ClassificationResult
from panelin_v4.engine.parser import parse_request, QuoteRequest
from panelin_v4.engine.sre_engine import calculate_sre, SREResult
from panelin_v4.engine.bom_engine import calculate_bom, BOMResult
from panelin_v4.engine.pricing_engine import calculate_pricing, PricingResult
from panelin_v4.engine.validation_engine import validate_quotation, ValidationResult
from panelin_v4.engine.quotation_engine import process_quotation, QuotationOutput


class QuotationService:
    """Servicio de cotización que orquesta el motor panelin_v4.

    Expone cada etapa del pipeline de forma individual (para Steps del workflow)
    y como pipeline completo (para uso directo en herramientas).

    Diseño:
    - Cada método es PURO y DETERMINÍSTICO — sin LLM, sin IO
    - Costo: $0.00 por llamada (solo CPU Python)
    - Thread-safe (sin estado compartido)
    """

    def classify(self, text: str, force_mode: Optional[str] = None) -> ClassificationResult:
        """Etapa 1: Clasificar tipo y modo de la solicitud.

        Returns:
            ClassificationResult con request_type (roof/wall/accessories/etc)
            y operating_mode (informativo/pre_cotizacion/formal)
        """
        return classify_request(text, force_mode=force_mode)

    def parse(self, text: str) -> QuoteRequest:
        """Etapa 2: Parsear texto libre en QuoteRequest estructurado.

        Extrae: familia, sub_familia, espesor, dimensiones, cliente, accesorios.
        Tolerante a ruido y variaciones del español rioplatense.
        """
        return parse_request(text)

    def calculate_sre(self, request: QuoteRequest) -> SREResult:
        """Etapa 3: Structural Risk Engine — score 0-100.

        Componentes:
            R_datos (0-40): completitud de datos
            R_autoportancia (0-50): relación vano/autoportancia
            R_geometria (0-15): complejidad geométrica
            R_sistema (0-15): sensibilidad del sistema

        Score < 30 → Nivel 3 (requiere datos); > 85 → Bloqueo técnico.
        """
        return calculate_sre(request)

    def calculate_bom(self, request: QuoteRequest) -> BOMResult:
        """Etapa 4: Bill of Materials — lista de materiales con cantidades.

        Usa bom_rules.json para seleccionar sistema constructivo y calcular:
        - Cantidad de paneles
        - Accesorios (goteros, babetas, cumbrera, perfiles, fijaciones, silicona)
        - Puntos de fijación y apoyos

        NUNCA inventa materiales — todo viene de bom_rules.json + accessories_catalog.json.
        """
        geo = request.geometry
        return calculate_bom(
            familia=request.familia or "ISOROOF",
            sub_familia=request.sub_familia or "STANDARD",
            thickness_mm=request.thickness_mm or 50,
            uso=request.uso or "techo",
            length_m=(geo.length_m if geo and geo.length_m else 0.0),
            width_m=(geo.width_m if geo and geo.width_m else 0.0),
            structure_type=request.structure_type or "metal",
            panel_count=(geo.panel_count if geo else None),
            panel_lengths=(geo.panel_lengths if geo else None),
            roof_type=request.roof_type,
            span_m=request.span_m,
        )

    def calculate_pricing(
        self,
        bom: BOMResult,
        request: QuoteRequest,
    ) -> PricingResult:
        """Etapa 5: Pricing — precios exclusivamente del KB.

        IVA 22% SIEMPRE incluido (precios finales al cliente).
        Si no se encuentra precio → missing_prices[], NUNCA inventa.
        """
        return calculate_pricing(
            bom=bom,
            familia=request.familia or "ISOROOF",
            sub_familia=request.sub_familia or "STANDARD",
            thickness_mm=request.thickness_mm or 50,
            panel_area_m2=bom.area_m2,
            iva_mode="incluido",
        )

    def validate(
        self,
        request: QuoteRequest,
        sre: SREResult,
        bom: BOMResult,
        pricing: PricingResult,
        mode: str,
    ) -> ValidationResult:
        """Etapa 6: Validación 4 capas.

        Capas:
            A - Integridad: familia/espesor presentes, precios encontrados
            B - Técnica: vano para techo en modo formal, autoportancia
            C - Comercial: flete sin localidad, techo sin accesorios
            D - Matemática: total=0, descuadre subtotales

        En modo pre_cotizacion: CRITICOs no-matemáticos se degradan a WARNING.
        """
        return validate_quotation(
            request=request,
            sre=sre,
            bom=bom,
            pricing=pricing,
            mode=mode,
        )

    def full_pipeline(
        self,
        text: str,
        force_mode: Optional[str] = None,
        client_name: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> QuotationOutput:
        """Pipeline completo 9 etapas — para uso en herramientas y tests.

        Internamente llama a panelin_v4.engine.quotation_engine.process_quotation().
        El resultado incluye SAI score y status final.
        """
        kwargs: Dict[str, Any] = {"text": text}
        if force_mode:
            kwargs["force_mode"] = force_mode
        if client_name:
            kwargs["client_name"] = client_name
        return process_quotation(**kwargs)

    def output_to_dict(self, output: QuotationOutput) -> Dict[str, Any]:
        """Convierte QuotationOutput a dict serializable para JSON/API."""
        return output.to_dict() if hasattr(output, "to_dict") else asdict(output)


_service_singleton: Optional[QuotationService] = None


def get_quotation_service() -> QuotationService:
    """Retorna la instancia singleton del servicio de cotización."""
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = QuotationService()
    return _service_singleton
