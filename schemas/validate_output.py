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
SCHEMA_V6_PATH = Path(__file__).parent / "quote_output_v6.schema.json"


def load_schema(version: str = "auto") -> dict:
    if version == "v6":
        path = SCHEMA_V6_PATH
    elif version == "v1":
        path = SCHEMA_PATH
    else:
        path = SCHEMA_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def detect_schema_version(data: dict) -> str:
    """Auto-detect whether data follows v1 or v6 schema."""
    if "paneles" in data or "empresa" in data:
        return "v6"
    if "meta" in data or "subsystems" in data:
        return "v1"
    return "v1"


def validate_quote(quote_data: dict, schema: dict = None) -> list[str]:
    """
    Validate a quote output dict against the schema.
    Auto-detects v1 vs v6 format if no schema provided.

    Returns a list of error messages (empty if valid).
    """
    if schema is None:
        version = detect_schema_version(quote_data)
        schema = load_schema(version)

    if HAS_JSONSCHEMA:
        validator = jsonschema.Draft202012Validator(schema)
        return [
            f"{'.'.join(str(p) for p in err.absolute_path)}: {err.message}"
            if err.absolute_path else err.message
            for err in sorted(validator.iter_errors(quote_data), key=lambda e: list(e.path))
        ]

    errors = []

    # v6 format validation
    if "paneles" in quote_data:
        for field in ("empresa", "cotizacion", "cliente", "paneles", "accesorios", "anclaje", "traslado", "comentarios"):
            if field not in quote_data:
                errors.append(f"Missing required field: '{field}'")
        for i, p in enumerate(quote_data.get("paneles", [])):
            for pf in ("nombre", "seccion", "largo_m", "cantidad", "ancho_util_m", "precio_m2", "costo_m2"):
                if pf not in p:
                    errors.append(f"paneles[{i}]: missing '{pf}'")
        for i, a in enumerate(quote_data.get("accesorios", [])):
            for af in ("nombre", "largo_m", "cantidad", "precio_ml", "costo_ml"):
                if af not in a:
                    errors.append(f"accesorios[{i}]: missing '{af}'")
        for i, a in enumerate(quote_data.get("anclaje", [])):
            for af in ("nombre", "cantidad", "precio_unit", "costo_real"):
                if af not in a:
                    errors.append(f"anclaje[{i}]: missing '{af}'")
        return errors

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
