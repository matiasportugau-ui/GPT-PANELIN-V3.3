#!/usr/bin/env python3
"""
Generate wolf_api/catalog.json from bromyros_pricing_gpt_optimized.json.

Transforms the 96-product bromyros pricing database into the flat
{product_id: {price_usd, name, description, ...}} format expected by
wolf_api/main.py _load_catalog().

Usage:
    python scripts/generate_catalog.py
    python scripts/generate_catalog.py --source path/to/bromyros.json --output path/to/catalog.json
    python scripts/generate_catalog.py --dry-run   # preview without writing

The catalog uses `sale_iva_inc` as the canonical price (IVA 22% included)
because that is the customer-facing price used in quotations.

Product IDs are generated in two forms for maximum discoverability:
  - By SKU:  "IROOF30" → the raw SKU from the pricing matrix
  - By key:  "ISODEC_EPS_100mm" → familia_subfamilia_thickness (for panels)

This ensures compatibility with both the OpenAPI schema (which documents
product_id examples like "ISOPANEL_EPS_50mm") and the raw SKU codes
that power users might know.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "bromyros_pricing_gpt_optimized.json"
DEFAULT_OUTPUT = REPO_ROOT / "wolf_api" / "catalog.json"

# Product types that are panels (priced per m²)
PANEL_TIPOS = {"Panel", "PANEL EPS", "PANEL PIR"}


def _build_panel_key(product: dict) -> str | None:
    """Build a human-friendly product_id like ISODEC_EPS_100mm for panels."""
    familia = product.get("familia", "")
    sub_familia = product.get("sub_familia", "")
    thickness = product.get("specifications", {}).get("thickness_mm")

    if not familia or thickness is None:
        return None

    # Normalize familia → clean key
    familia_key = (
        familia.upper()
        .replace(" / FOIL", "_FOIL")
        .replace(" / ", "_")
        .replace(" ", "_")
        .strip()
    )

    # Normalize sub_familia
    sub_key = sub_familia.upper().strip() if sub_familia else ""
    if sub_key in ("ESTANDAR", ""):
        sub_key = ""

    # Thickness as integer
    thick_int = int(thickness) if thickness == int(thickness) else thickness

    if sub_key:
        return f"{familia_key}_{sub_key}_{thick_int}mm"
    else:
        return f"{familia_key}_{thick_int}mm"


def _build_description(product: dict) -> str:
    """Build a searchable description string from product metadata."""
    parts = []
    parts.append(product.get("name", ""))

    familia = product.get("familia", "")
    if familia:
        parts.append(f"Familia: {familia}")

    sub = product.get("sub_familia", "")
    if sub and sub.lower() != "estandar":
        parts.append(f"Subfamilia: {sub}")

    tipo = product.get("tipo", "")
    if tipo:
        parts.append(f"Tipo: {tipo}")

    specs = product.get("specifications", {})
    thick = specs.get("thickness_mm")
    if thick is not None:
        parts.append(f"Espesor: {int(thick) if thick == int(thick) else thick}mm")

    unit = specs.get("unit_base", "")
    if unit:
        parts.append(f"Unidad: {unit}")

    largo = specs.get("largo_min_max", "")
    if largo:
        parts.append(f"Largo: {largo} m")

    return " | ".join(parts)


def generate_catalog(source_path: Path) -> dict:
    """Read bromyros pricing and produce the flat catalog dict."""
    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    if not products:
        print(f"ERROR: No products found in {source_path}", file=sys.stderr)
        sys.exit(1)

    catalog: dict[str, dict] = {}
    stats = {"total": 0, "panels": 0, "accessories": 0, "by_sku": 0, "by_key": 0, "skipped_no_price": 0}

    for product in products:
        sku = product.get("sku", "").strip()
        if not sku:
            continue

        pricing = product.get("pricing", {})
        price_usd = pricing.get("sale_iva_inc")

        if price_usd is None or price_usd == 0:
            stats["skipped_no_price"] += 1
            continue

        tipo = product.get("tipo", "")
        is_panel = tipo in PANEL_TIPOS
        specs = product.get("specifications", {})

        entry = {
            "name": product.get("name", sku),
            "price_usd": price_usd,
            "price_sin_iva": pricing.get("sale_sin_iva"),
            "web_price_usd": pricing.get("web_iva_inc"),
            "familia": product.get("familia", ""),
            "sub_familia": product.get("sub_familia", ""),
            "tipo": tipo,
            "unit": specs.get("unit_base", "m2" if is_panel else "unid"),
            "thickness_mm": specs.get("thickness_mm"),
            "length_m": specs.get("length_m"),
            "description": _build_description(product),
            "available": True,
            "stock": "disponible",
        }

        # Always index by raw SKU
        catalog[sku] = entry
        stats["by_sku"] += 1

        # For panels, also index by human-friendly key (ISODEC_EPS_100mm)
        if is_panel:
            panel_key = _build_panel_key(product)
            if panel_key and panel_key != sku:
                catalog[panel_key] = entry
                stats["by_key"] += 1
            stats["panels"] += 1
        else:
            stats["accessories"] += 1

        stats["total"] += 1

    return catalog, stats, data.get("metadata", {})


def main():
    parser = argparse.ArgumentParser(
        description="Generate wolf_api/catalog.json from bromyros pricing data"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Source bromyros pricing file (default: {DEFAULT_SOURCE.name})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output catalog file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output without writing file",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"ERROR: Source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    print(f"Source: {args.source}")
    print(f"Output: {args.output}")
    print()

    catalog, stats, source_meta = generate_catalog(args.source)

    # Wrap with metadata
    output = catalog  # wolf_api expects flat dict: {product_id: {fields}}

    print("═" * 50)
    print("  CATALOG GENERATION RESULTS")
    print("═" * 50)
    print(f"  Source products:        {stats['total']}")
    print(f"    Panels:               {stats['panels']}")
    print(f"    Accessories:          {stats['accessories']}")
    print(f"    Skipped (no price):   {stats['skipped_no_price']}")
    print(f"  Catalog entries:        {len(catalog)}")
    print(f"    By SKU:               {stats['by_sku']}")
    print(f"    By panel key:         {stats['by_key']}")
    print(f"  Source version:         {source_meta.get('version', '?')}")
    print(f"  Source date:            {source_meta.get('generated_at', '?')}")
    print()

    # Show sample entries
    print("Sample entries:")
    for i, (pid, pdata) in enumerate(catalog.items()):
        if i >= 5:
            print(f"  ... and {len(catalog) - 5} more")
            break
        print(f"  {pid}: {pdata['name']} → USD {pdata['price_usd']} ({pdata['unit']})")

    if args.dry_run:
        print()
        print("DRY RUN — no file written")
        return

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    file_size = args.output.stat().st_size
    print()
    print(f"✅ Written: {args.output} ({file_size:,} bytes)")


if __name__ == "__main__":
    main()
