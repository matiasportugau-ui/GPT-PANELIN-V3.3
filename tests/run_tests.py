#!/usr/bin/env python3
"""
YAML Test Runner for Panelin Envelope Engine
=============================================

Loads test scenarios from tests/*.yaml and validates them against
the structured rules and KB data.

Usage:
  python tests/run_tests.py              # run all tests
  python tests/run_tests.py -v           # verbose output
  python tests/run_tests.py -k span      # filter by name pattern
"""

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required. Install: pip install pyyaml")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "kb"
RULES_DIR = ROOT / "rules"
TESTS_DIR = ROOT / "tests"


class TestContext:
    """Loads KB and rules data for test evaluation."""

    def __init__(self):
        self.catalog = self._load_csv(KB_DIR / "catalog.csv")
        self.pricing = self._load_csv(KB_DIR / "pricing.csv")
        self.autoportancia = self._load_csv(KB_DIR / "autoportancia.csv")
        self.accessories_map = self._load_json(KB_DIR / "accessories_map.json")
        self.validations_h = self._load_json(RULES_DIR / "validations_horizontal.json")
        self.validations_v = self._load_json(RULES_DIR / "validations_vertical.json")
        self.bom_h = self._load_json(RULES_DIR / "bom_rules_horizontal.json")
        self.bom_v = self._load_json(RULES_DIR / "bom_rules_vertical.json")
        self.schema = self._load_json(ROOT / "schemas" / "quote_output.schema.json")

    @staticmethod
    def _load_csv(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _load_json(path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.messages: list[str] = []

    def fail(self, msg: str):
        self.passed = False
        self.messages.append(f"FAIL: {msg}")

    def info(self, msg: str):
        self.messages.append(f"INFO: {msg}")

    def ok(self, msg: str):
        self.messages.append(f"  OK: {msg}")


def evaluate_hard_stop(ctx: TestContext, test_input: dict) -> str | None:
    """Evaluate P0 hard-stops against input data."""
    envelope = test_input.get("envelope_class", "")

    if envelope == "HORIZONTAL" or envelope == "UNIT_COMPLETE":
        horiz_input = test_input if envelope == "HORIZONTAL" else test_input.get("horizontal", {})

        for v in ctx.validations_h.get("validations", []):
            if not v.get("p0_hard_stop"):
                continue

            req_fields = v.get("required_fields", [])
            for field in req_fields:
                if field not in horiz_input or horiz_input[field] is None:
                    return v["hard_stop_message"]

            if v.get("requires_autoportancia_match"):
                family = horiz_input.get("panel_family", "")
                thickness = horiz_input.get("thickness_mm")
                span = horiz_input.get("span_m")

                match_found = False
                for row in ctx.autoportancia:
                    row_family = row.get("family", "")
                    row_thick = row.get("thickness_mm", "")
                    row_span_max = row.get("span_m_max", "")

                    if not row_span_max or row_span_max == "PLACEHOLDER":
                        continue

                    family_match = (
                        family.upper() in row_family.upper()
                        or row_family.upper() in family.upper()
                    )
                    thick_match = str(thickness) == str(row_thick)

                    if family_match and thick_match:
                        try:
                            if span and float(span) <= float(row_span_max):
                                match_found = True
                                break
                        except (ValueError, TypeError):
                            continue

                if not match_found:
                    return v["hard_stop_message"]

    if test_input.get("pricing_available") is False:
        return "No tengo esa información en mi base de conocimiento"

    return None


def find_skus_for_input(ctx: TestContext, test_input: dict) -> list[str]:
    """Find SKUs that would be included in the quote based on input."""
    found = []
    family = test_input.get("panel_family", "")

    for row in ctx.catalog:
        row_family = row.get("family", "")
        if family and (family.upper() in row_family.upper()
                       or row_family.upper() in family.upper()):
            found.append(row["sku_id"])

    for rule in ctx.accessories_map.get("rules", []):
        rule_family = rule.get("family", "")
        if family.upper() in rule_family.upper() or rule_family.upper() in family.upper():
            for sku in rule.get("accessories", {}).values():
                found.append(sku)

    return list(set(found))


def check_ambiguity(ctx: TestContext, test_input: dict) -> list[str]:
    """Check if an accessory request would be ambiguous."""
    request = test_input.get("accessory_request", "")
    if not request:
        return []

    matches = []
    for rule in ctx.accessories_map.get("rules", []):
        synonyms = rule.get("synonyms", {})
        for synonym, key in synonyms.items():
            if request.lower() in synonym.lower() or synonym.lower() in request.lower():
                if key not in matches:
                    matches.append(key)

    return matches


def run_test(ctx: TestContext, test_data: dict, verbose: bool = False) -> TestResult:
    """Run a single test scenario."""
    name = test_data.get("name", "unknown")
    result = TestResult(name)
    test_input = test_data.get("input", {})
    expect = test_data.get("expect", {})

    expected_hard_stop = expect.get("hard_stop")
    actual_hard_stop = evaluate_hard_stop(ctx, test_input)

    if expected_hard_stop is None and actual_hard_stop is None:
        result.ok("No hard-stop (expected none)")
    elif expected_hard_stop is None and actual_hard_stop is not None:
        result.fail(f"Unexpected hard-stop: '{actual_hard_stop}'")
    elif expected_hard_stop is not None and actual_hard_stop is None:
        result.fail(f"Expected hard-stop '{expected_hard_stop}' but got none")
    elif expected_hard_stop != actual_hard_stop:
        result.fail(f"Hard-stop mismatch:\n    expected: '{expected_hard_stop}'\n    actual:   '{actual_hard_stop}'")
    else:
        result.ok(f"Hard-stop matches: '{expected_hard_stop}'")

    if actual_hard_stop and expected_hard_stop:
        return result

    expected_skus = expect.get("includes_skus", [])
    if expected_skus:
        available_skus = find_skus_for_input(ctx, test_input)
        for sku in expected_skus:
            if sku in available_skus:
                result.ok(f"SKU '{sku}' found in catalog")
            else:
                result.fail(f"SKU '{sku}' NOT found in catalog for family '{test_input.get('panel_family')}'")

    if expect.get("separate_subtotals"):
        has_vert = "vertical" in test_input
        has_horiz = "horizontal" in test_input
        if has_vert and has_horiz:
            result.ok("UNIT_COMPLETE has both vertical and horizontal subsystems")
        else:
            result.fail("UNIT_COMPLETE missing vertical or horizontal subsystem")

    if expect.get("ambiguity_resolution") or expect.get("must_not_auto_select"):
        matches = check_ambiguity(ctx, test_input)
        if len(matches) > 1:
            result.ok(f"Ambiguity detected: {matches} (would require disambiguation)")
        elif len(matches) == 1:
            result.fail(f"Only 1 match for '{test_input.get('accessory_request')}': {matches} - no ambiguity to resolve")
        else:
            result.fail(f"No matches for '{test_input.get('accessory_request')}' - cannot test ambiguity")

    if expect.get("requires_autoportancia_match"):
        family = test_input.get("panel_family", "")
        thickness = test_input.get("thickness_mm")
        found = any(
            (family.upper() in r.get("family", "").upper() or
             r.get("family", "").upper() in family.upper())
            and str(thickness) == str(r.get("thickness_mm", ""))
            for r in ctx.autoportancia
        )
        if found:
            result.ok(f"Autoportancia record found for {family}/{thickness}mm")
        else:
            result.fail(f"No autoportancia record for {family}/{thickness}mm")

    return result


def main():
    parser = argparse.ArgumentParser(description="Panelin YAML Test Runner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-k", "--filter", type=str, default="", help="Filter tests by name pattern")
    args = parser.parse_args()

    print("=" * 60)
    print("Panelin Envelope Engine - Test Runner")
    print("=" * 60)

    ctx = TestContext()
    print(f"\nLoaded KB: {len(ctx.catalog)} catalog entries, "
          f"{len(ctx.pricing)} prices, "
          f"{len(ctx.autoportancia)} autoportancia records\n")

    test_files = sorted(TESTS_DIR.glob("test_*.yaml"))
    if not test_files:
        print("No test files found in tests/")
        sys.exit(1)

    results = []
    for tf in test_files:
        with open(tf, encoding="utf-8") as f:
            test_data = yaml.safe_load(f)

        if not test_data:
            continue

        test_name = test_data.get("name", tf.stem)
        if args.filter and args.filter.lower() not in test_name.lower():
            continue

        result = run_test(ctx, test_data, args.verbose)
        results.append(result)

        status = "PASS" if result.passed else "FAIL"
        icon = "+" if result.passed else "X"
        print(f"  [{icon}] {status}: {result.name}")

        if args.verbose or not result.passed:
            for msg in result.messages:
                print(f"      {msg}")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
