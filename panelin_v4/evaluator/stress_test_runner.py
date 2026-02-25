"""
Panelin v4.0 - Stress Test Runner
====================================

Simulates high-volume batch processing with mixed request types:
    - 40% incomplete requests
    - 30% ambiguous requests
    - 20% update requests
    - 10% complete requests

Measures:
    - Processing time per quotation
    - SAI score distribution
    - Blocking rate
    - Error rate
    - Consistency under load
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from panelin_v4.engine.quotation_engine import QuotationOutput, process_quotation
from panelin_v4.engine.classifier import OperatingMode
from panelin_v4.evaluator.sai_engine import calculate_sai


# Representative stress test inputs
STRESS_INPUTS: list[dict] = [
    # ── Complete requests (10%) ──
    {"text": "Isodec EPS 100 mm / 10 paneles de 5 mts / techo completo a metal + flete Montevideo",
     "client_name": "Test Client 1", "client_location": "Montevideo"},
    {"text": "Isopanel EPS 50 mm / 8 paneles de 2.40 mts / pared completa + flete",
     "client_name": "Test Client 2", "client_location": "Maldonado"},
    {"text": "Isoroof 50 mm / 12 paneles de 4.60 mts / techo 2 aguas completo a madera + flete",
     "client_name": "Test Client 3", "client_location": "Punta del Este"},

    # ── Incomplete requests (40%) ──
    {"text": "Isodec 100 mm / techo 7 ancho x 10 largo"},
    {"text": "Isodec 150 mm / 3 paneles"},
    {"text": "Isopanel / pared 4.50 x 8.50"},
    {"text": "Isoroof 30 mm / ver plano"},
    {"text": "Isodec 200 mm / 5 paneles de 11 mts"},
    {"text": "techo de 8 metros de luz"},
    {"text": "Isopanel 100 mm / 3 paredes / 45 + 15 + 45 / de 2 m de alto"},
    {"text": "Isodec 150 mm"},
    {"text": "6 goteros frontales + 4 laterales 100mm"},
    {"text": "panel techo 3.60"},
    {"text": "Isodec EPS 100 mm / 8 paneles"},
    {"text": "cubierta 200 mm / 16 paneles de 8.10 m de largo"},

    # ── Ambiguous requests (30%) ──
    {"text": "Isodec 100 mm / 6p de 3mts + Isopanel 100 mm / 3p de 2.54 mts"},
    {"text": "Isopanel 200 mm y 100/150 / Habitacion completa 4.50 x 8.50 / altura 2,5 y 3 mts"},
    {"text": "3 opciones / Isodec 150, 200 y 250 mm / 13 p. de 10 m / completo a metal + flete"},
    {"text": "2 opciones / Isodec 150 y 200 mm / 9p de 9 mts / frontal gotero o canalón"},
    {"text": "Canalón para chapa de 10 cm, necesito 10 mts de canalon"},
    {"text": "Isodec 100 mm / techo 9x6"},
    {"text": "Isodec 50 y 100 mm / 3x3 x puerta"},
    {"text": "2 opciones: Isoroof 80 mm y Isodec 150 mm GRIS / 5 paneles de 11 mts + 6 paneles de 6 metros"},
    {"text": "Barbacoa de 11 x 5 m / Isopanel 100 mm h 3m + Isodec 11 p. de 6 m"},

    # ── Update requests (20%) ──
    {"text": "Actualizar cotización Montfrío - agregar 1 isopanel 100mm de 2.40m"},
    {"text": "ACTUALIZAR PRESUPUESTO / Isopanel 100 mm / 3 p. de 2,30 m"},
    {"text": "Actualizar presupuesto y reenviar"},
    {"text": "Solo precio del panel de fachada Isopanel 100 mm / 3 de 2,30 m + 1 de 3,05 m"},
    {"text": "Dividir cotización en 2 casas / Isodec 100mm"},
    {"text": "Agregar 1 panel techo 3.60 + 1 ángulo aluminio"},
]


@dataclass
class StressTestResult:
    total_requests: int = 0
    processed: int = 0
    blocked: int = 0
    draft: int = 0
    requires_review: int = 0
    validated: int = 0
    avg_processing_ms: float = 0.0
    max_processing_ms: float = 0.0
    avg_sai: float = 0.0
    min_sai: float = 100.0
    max_sai: float = 0.0
    sai_pass_rate: float = 0.0
    blocking_rate: float = 0.0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "processed": self.processed,
            "blocked": self.blocked,
            "draft": self.draft,
            "requires_review": self.requires_review,
            "validated": self.validated,
            "avg_processing_ms": round(self.avg_processing_ms, 2),
            "max_processing_ms": round(self.max_processing_ms, 2),
            "avg_sai": round(self.avg_sai, 1),
            "min_sai": round(self.min_sai, 1),
            "max_sai": round(self.max_sai, 1),
            "sai_pass_rate": round(self.sai_pass_rate, 1),
            "blocking_rate": round(self.blocking_rate, 1),
            "error_count": self.error_count,
            "errors": self.errors[:10],
        }


def run_stress_test(
    inputs: list[dict] | None = None,
    mode: OperatingMode = OperatingMode.PRE_COTIZACION,
) -> StressTestResult:
    """Run stress test against the quotation engine.

    Args:
        inputs: List of request dicts. Uses STRESS_INPUTS by default.
        mode: Force operating mode for all requests.

    Returns:
        StressTestResult with aggregate metrics.
    """
    test_inputs = inputs or STRESS_INPUTS
    result = StressTestResult(total_requests=len(test_inputs))

    processing_times: list[float] = []
    sai_scores: list[float] = []

    for req in test_inputs:
        try:
            start = time.perf_counter()
            output = process_quotation(
                text=req.get("text", ""),
                force_mode=mode,
                client_name=req.get("client_name"),
                client_location=req.get("client_location"),
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            processing_times.append(elapsed_ms)

            sai = calculate_sai(output)
            sai_scores.append(sai.score)

            result.processed += 1

            if output.status == "blocked":
                result.blocked += 1
            elif output.status == "requires_review":
                result.requires_review += 1
            elif output.status == "validated":
                result.validated += 1
            else:
                result.draft += 1

        except Exception as e:
            result.error_count += 1
            result.errors.append(f"{req.get('text', '')[:60]}... -> {str(e)}")

    if processing_times:
        result.avg_processing_ms = sum(processing_times) / len(processing_times)
        result.max_processing_ms = max(processing_times)

    if sai_scores:
        result.avg_sai = sum(sai_scores) / len(sai_scores)
        result.min_sai = min(sai_scores)
        result.max_sai = max(sai_scores)
        passed = sum(1 for s in sai_scores if s >= 80)
        result.sai_pass_rate = passed / len(sai_scores) * 100

    if result.processed > 0:
        result.blocking_rate = result.blocked / result.processed * 100

    return result
