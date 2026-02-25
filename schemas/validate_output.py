#!/usr/bin/env python3
"""
Schema validation for Panelin quote outputs.

Validates quote JSON objects against schemas/quote_output.schema.json.

Usage:
  python schemas/validate_output.py quote.json
  python schemas/validate_output.py --example   # validate built-in example
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SCHEMA_PATH = Path(__file__).parent / "quote_output.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_quote(quote_data: dict, schema: dict = None) -> list[str]:
    """
    Validate a quote output dict against the schema.

    Returns a list of error messages (empty if valid).
    """
    if schema is None:
        schema = load_schema()

    if HAS_JSONSCHEMA:
        validator = jsonschema.Draft202012Validator(schema)
        return [
            f"{'.'.join(str(p) for p in err.absolute_path)}: {err.message}"
            if err.absolute_path else err.message
            for err in sorted(validator.iter_errors(quote_data), key=lambda e: list(e.path))
        ]

    errors = []
    for field in schema.get("required", []):
        if field not in quote_data:
            errors.append(f"Missing required field: '{field}'")

    meta = quote_data.get("meta", {})
    if meta:
        for mf in schema.get("properties", {}).get("meta", {}).get("required", []):
            if mf not in meta:
                errors.append(f"Missing required field in meta: '{mf}'")

    iva_mode = quote_data.get("iva_mode")
    if iva_mode and iva_mode not in ("incluido", "discriminado"):
        errors.append(f"iva_mode must be 'incluido' or 'discriminado', got '{iva_mode}'")

    subsystems = quote_data.get("subsystems", [])
    for i, sub in enumerate(subsystems):
        for sf in ("envelope_class", "inputs", "line_items", "subtotal"):
            if sf not in sub:
                errors.append(f"subsystems[{i}]: missing '{sf}'")
        for j, item in enumerate(sub.get("line_items", [])):
            for lf in ("sku_id", "description", "qty", "unit"):
                if lf not in item:
                    errors.append(f"subsystems[{i}].line_items[{j}]: missing '{lf}'")

    totals = quote_data.get("totals", {})
    for tf in ("net", "iva", "gross"):
        if tf not in totals:
            errors.append(f"totals: missing '{tf}'")

    return errors


EXAMPLE_QUOTE = {
    "meta": {
        "quote_id": "Q-2026-0001",
        "created_at": "2026-02-25T12:00:00Z",
        "engine_version": "3.2",
    },
    "iva_mode": "incluido",
    "currency": "USD",
    "subsystems": [
        {
            "envelope_class": "VERTICAL",
            "inputs": {"panel_family": "ISOWALL", "thickness_mm": 50, "area_m2": 100},
            "line_items": [
                {
                    "sku_id": "IW50",
                    "description": "Isowall 50mm PIR",
                    "qty": 100,
                    "unit": "m2",
                    "unit_price": 57.03,
                    "net": 5703.0,
                    "iva_rate": 0.22,
                    "iva_amount": None,
                    "gross": None,
                    "trace": {"rule_id": "V-ISOWALL-PIR", "formula": "area_m2"},
                },
            ],
            "subtotal": {"net": 5703.0, "iva": None, "gross": None},
        },
    ],
    "totals": {"net": 5703.0, "iva": None, "gross": None},
    "hard_stops": [],
}


def main():
    parser = argparse.ArgumentParser(description="Validate Panelin quote output")
    parser.add_argument("file", nargs="?", help="JSON file to validate")
    parser.add_argument("--example", action="store_true", help="Validate built-in example")
    args = parser.parse_args()

    schema = load_schema()

    if args.example:
        data = EXAMPLE_QUOTE
        source = "built-in example"
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
        source = args.file
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Validating: {source}")
    print(f"Schema: {SCHEMA_PATH}")
    print(f"Validator: {'jsonschema' if HAS_JSONSCHEMA else 'basic (install jsonschema for full)'}\n")

    errors = validate_quote(data, schema)

    if errors:
        print(f"INVALID - {len(errors)} error(s):\n")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("VALID - Quote output conforms to schema")
        sys.exit(0)


if __name__ == "__main__":
    main()
