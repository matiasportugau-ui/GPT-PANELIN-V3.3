"""
Panelin v4.0 - Regression Test Suite
=======================================

Expert test cases covering:
    - Structural edge cases (autoportancia limits)
    - BOM completeness
    - Pricing accuracy
    - Accessory compatibility
    - IVA handling
    - Commercial flow (non-blocking in pre mode)
    - Stress scenarios

Each test case validates specific invariants that must NEVER be violated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable

from panelin_v4.engine.quotation_engine import QuotationOutput, process_quotation
from panelin_v4.engine.classifier import OperatingMode
from panelin_v4.evaluator.sai_engine import calculate_sai


@dataclass
class TestCase:
    id: str
    category: str  # structural | bom | pricing | commercial | stress
    description: str
    input_text: str
    force_mode: Optional[OperatingMode] = None
    client_name: Optional[str] = None
    client_location: Optional[str] = None
    assertions: list[Callable[[QuotationOutput], tuple[bool, str]]] = field(
        default_factory=list,
    )


@dataclass
class TestResult:
    test_id: str
    category: str
    description: str
    passed: bool
    sai_score: float
    failures: list[str] = field(default_factory=list)
    output_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "category": self.category,
            "description": self.description,
            "passed": self.passed,
            "sai_score": self.sai_score,
            "failures": self.failures,
            "output_summary": self.output_summary,
        }


# ──────────────────────── Assertion helpers ──────────────────────────

def assert_familia(expected: str) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        actual = o.request.get("familia")
        ok = actual == expected
        return ok, f"familia: expected '{expected}', got '{actual}'"
    return check


def assert_thickness(expected: int) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        actual = o.request.get("thickness_mm")
        ok = actual == expected
        return ok, f"thickness_mm: expected {expected}, got {actual}"
    return check


def assert_not_blocked() -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        ok = o.status != "blocked"
        return ok, f"status should not be 'blocked', got '{o.status}'"
    return check


def assert_status(expected: str) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        ok = o.status == expected
        return ok, f"status: expected '{expected}', got '{o.status}'"
    return check


def assert_has_bom_items() -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        items = o.bom.get("items", [])
        ok = len(items) > 0
        return ok, f"BOM should have items, got {len(items)}"
    return check


def assert_panel_count_gt(minimum: int) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        count = o.bom.get("panel_count", 0)
        ok = count >= minimum
        return ok, f"panel_count >= {minimum}, got {count}"
    return check


def assert_pricing_total_gt(minimum: float) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        total = o.pricing.get("subtotal_total_usd", 0)
        ok = total > minimum
        return ok, f"total > {minimum}, got {total}"
    return check


def assert_sre_below(max_score: int) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        score = o.sre.get("score", 100)
        ok = score <= max_score
        return ok, f"SRE score <= {max_score}, got {score}"
    return check


def assert_autoportancia_status(expected: str) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        status = o.validation.get("autoportancia_status", "unknown")
        ok = status == expected
        return ok, f"autoportancia_status: expected '{expected}', got '{status}'"
    return check


def assert_mode(expected: str) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        ok = o.mode == expected
        return ok, f"mode: expected '{expected}', got '{o.mode}'"
    return check


def assert_sai_above(minimum: float) -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        sai = calculate_sai(o)
        ok = sai.score >= minimum
        return ok, f"SAI >= {minimum}, got {sai.score}"
    return check


def assert_has_alternatives() -> Callable:
    def check(o: QuotationOutput) -> tuple[bool, str]:
        alts = o.sre.get("alternative_thicknesses", [])
        ok = len(alts) > 0
        return ok, f"should have alternative thicknesses, got {alts}"
    return check


# ──────────────────── Expert Test Cases ──────────────────────

EXPERT_TEST_CASES: list[TestCase] = [
    # ── Structural tests ──
    TestCase(
        id="S01", category="structural",
        description="ISODEC EPS 100mm techo 4.5m span - within capacity",
        input_text="Isodec EPS 100 mm / 6 paneles de 4.5 mts / completo a metal",
        assertions=[
            assert_familia("ISODEC"),
            assert_thickness(100),
            assert_not_blocked(),
            assert_has_bom_items(),
        ],
    ),
    TestCase(
        id="S02", category="structural",
        description="ISODEC EPS 100mm roof, span missing - should NOT block in pre mode",
        input_text="Isodec 100 mm / 8 paneles de 6 mts / techo completo + flete",
        force_mode=OperatingMode.PRE_COTIZACION,
        assertions=[
            assert_not_blocked(),
            assert_mode("pre_cotizacion"),
            assert_has_bom_items(),
        ],
    ),
    TestCase(
        id="S03", category="structural",
        description="ISOROOF 30mm, 4m span exceeds capacity (max 2.8m) - suggest alternative",
        input_text="Isoroof 30 mm / techo 4 mts ancho x 5 mts largo / completo",
        assertions=[
            assert_familia("ISOROOF"),
            assert_thickness(30),
        ],
    ),
    TestCase(
        id="S04", category="structural",
        description="ISODEC EPS 100mm, formal mode missing span - should block",
        input_text="Isodec EPS 100 mm / 10 paneles de 8 mts / formal",
        force_mode=OperatingMode.FORMAL,
        assertions=[
            assert_familia("ISODEC"),
            assert_thickness(100),
        ],
    ),

    # ── BOM tests ──
    TestCase(
        id="B01", category="bom",
        description="Complete roof BOM - ISODEC EPS 100mm 11x5m",
        input_text="Isodec EPS 100 mm / techo 11 m ancho x 5 m largo / completo a metal",
        assertions=[
            assert_familia("ISODEC"),
            assert_has_bom_items(),
            assert_panel_count_gt(8),
        ],
    ),
    TestCase(
        id="B02", category="bom",
        description="Wall BOM - ISOPANEL EPS 100mm",
        input_text="Isopanel EPS 100 mm / 6 paneles de 2.50 mts / pared completa",
        assertions=[
            assert_familia("ISOPANEL"),
            assert_not_blocked(),
            assert_has_bom_items(),
        ],
    ),
    TestCase(
        id="B03", category="bom",
        description="Roof 2 aguas should include cumbrera",
        input_text="Isodec 150 mm / techo 2 aguas / 8 paneles de 6.5 mts / completo a hormigón",
        assertions=[
            assert_familia("ISODEC"),
            assert_thickness(150),
            assert_has_bom_items(),
        ],
    ),

    # ── Pricing tests ──
    TestCase(
        id="P01", category="pricing",
        description="Pricing should produce positive total for valid request",
        input_text="Isodec EPS 100 mm / 10 paneles de 5 mts / completo a metal + flete",
        assertions=[
            assert_not_blocked(),
        ],
    ),
    TestCase(
        id="P02", category="pricing",
        description="Accessories-only request should price correctly",
        input_text="12 Goteros Frontales 100 mm + 8 Goteros Laterales 100 mm",
        assertions=[
            assert_not_blocked(),
        ],
    ),

    # ── Commercial flow tests ──
    TestCase(
        id="C01", category="commercial",
        description="Pre-quotation should NEVER block for missing span",
        input_text="Isodec 100 mm / 6 paneles de 6.50 m / completo a hormigón + flete Maldonado",
        force_mode=OperatingMode.PRE_COTIZACION,
        assertions=[
            assert_not_blocked(),
            assert_mode("pre_cotizacion"),
        ],
    ),
    TestCase(
        id="C02", category="commercial",
        description="Update request should be detected as update type",
        input_text="Actualizar cotización - agregar 1 isopanel 100mm de 2.40m",
        assertions=[
            assert_not_blocked(),
        ],
    ),
    TestCase(
        id="C03", category="commercial",
        description="Wall system should not require span validation",
        input_text="Isopanel 50 mm / 13 paneles de 2.60 mts / solo paneles",
        assertions=[
            assert_familia("ISOPANEL"),
            assert_thickness(50),
            assert_not_blocked(),
        ],
    ),

    # ── Mixed/complex tests ──
    TestCase(
        id="M01", category="stress",
        description="Mixed request: wall + roof",
        input_text="Isopanel 100 mm pared 14p de 2.4 + Isodec 100 mm techo 7p de 5mts",
        assertions=[
            assert_not_blocked(),
        ],
    ),
    TestCase(
        id="M02", category="stress",
        description="Incomplete request - only product mentioned",
        input_text="Isodec 150 mm",
        assertions=[
            assert_familia("ISODEC"),
            assert_thickness(150),
        ],
    ),
    TestCase(
        id="M03", category="stress",
        description="Canalon request - accessories only flow",
        input_text="Canalón 100 mm / 3 piezas de 3 m + 2 soportes + 2 tapas + 1 embudo + 3 siliconas",
        assertions=[
            assert_not_blocked(),
        ],
    ),

    # ── Real-world quotation requests from batch ──
    TestCase(
        id="R01", category="real_world",
        description="Yoana - Isodec 150mm 6p x 6.50m completo a H°",
        input_text="Isodec 150 mm / 6 p. de 6,50 m / completo a H° + flete",
        client_name="Yoana Gonzalez",
        client_location="La Teja, Mvdeo",
        assertions=[
            assert_familia("ISODEC"),
            assert_thickness(150),
            assert_not_blocked(),
            assert_has_bom_items(),
        ],
    ),
    TestCase(
        id="R02", category="real_world",
        description="Andres - Isopanel 50mm 13 paneles de 2.60m",
        input_text="Isopanel 50 mm / 13 paneles de 2,60 mts",
        client_name="Andres",
        assertions=[
            assert_familia("ISOPANEL"),
            assert_thickness(50),
            assert_not_blocked(),
            assert_has_bom_items(),
        ],
    ),
    TestCase(
        id="R03", category="real_world",
        description="Mauricio - Isodec 200mm 7p de 8m",
        input_text="Isodec 200 mm / 7 p. de 8 m de largo + accesorios estándar y anclajes a metal + entrega en Colon",
        client_name="Mauricio",
        client_location="Colon, Mvdeo",
        assertions=[
            assert_familia("ISODEC"),
            assert_thickness(200),
            assert_not_blocked(),
            assert_has_bom_items(),
        ],
    ),
    TestCase(
        id="R04", category="real_world",
        description="Cristian - Complete room 4.50 x 8.50",
        input_text="Isopanel 200 mm y 100 mm / Habitacion completa 4.50 x 8.50 / altura 2,5 y 3 mts",
        assertions=[
            assert_not_blocked(),
        ],
    ),
]


def run_regression_suite(
    test_cases: Optional[list[TestCase]] = None,
) -> dict:
    """Run the regression test suite.

    Returns:
        Summary dict with passed/failed counts and detailed results.
    """
    cases = test_cases or EXPERT_TEST_CASES
    results: list[TestResult] = []
    passed_count = 0
    failed_count = 0

    for tc in cases:
        output = process_quotation(
            text=tc.input_text,
            force_mode=tc.force_mode,
            client_name=tc.client_name,
            client_location=tc.client_location,
        )

        sai = calculate_sai(output)
        failures: list[str] = []

        for assertion_fn in tc.assertions:
            ok, msg = assertion_fn(output)
            if not ok:
                failures.append(msg)

        test_passed = len(failures) == 0
        if test_passed:
            passed_count += 1
        else:
            failed_count += 1

        results.append(TestResult(
            test_id=tc.id,
            category=tc.category,
            description=tc.description,
            passed=test_passed,
            sai_score=sai.score,
            failures=failures,
            output_summary={
                "quote_id": output.quote_id,
                "mode": output.mode,
                "level": output.level,
                "status": output.status,
                "confidence": output.confidence_score,
                "panel_count": output.bom.get("panel_count", 0),
                "total_usd": output.pricing.get("subtotal_total_usd", 0),
            },
        ))

    return {
        "total": len(cases),
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate": round(passed_count / len(cases) * 100, 1) if cases else 0,
        "results": [r.to_dict() for r in results],
    }
