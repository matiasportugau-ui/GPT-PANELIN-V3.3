#!/usr/bin/env python3
"""
Migrate production data from root-level JSON/CSV files into the new
structured kb/, rules/ directories.

Source files:
  - accessories_catalog.json -> kb/catalog.csv, kb/pricing.csv, kb/accessories_map.json
  - bom_rules.json           -> kb/autoportancia.csv, rules/bom_rules_*.json
  - normalized_full_cleaned.csv -> kb/catalog.csv (panels), kb/pricing.csv (panels)

Usage:
  python scripts/migrate_to_structured_kb.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "kb"
RULES_DIR = ROOT / "rules"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_csv_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Catalog ──────────────────────────────────────────────────────

def _system_for_compat(compat_list: list[str]) -> str:
    roof = {"ISODEC", "ISOROOF"}
    wall = {"ISOPANEL", "ISOWALL", "ISOFRIG"}
    has_roof = bool(set(compat_list) & roof)
    has_wall = bool(set(compat_list) & wall)
    if has_roof and has_wall:
        return "ALL"
    if has_roof:
        return "HORIZONTAL"
    if has_wall:
        return "VERTICAL"
    return "ALL"


def _family_for_compat(compat_list: list[str]) -> str:
    if len(compat_list) == 1:
        return compat_list[0]
    if "UNIVERSAL" in compat_list:
        return "UNIVERSAL"
    return ";".join(compat_list)


def _product_type(tipo: str) -> str:
    mapping = {
        "arandela": "fastener", "arandela_carrocero": "fastener",
        "arandela_trapezoidal": "fastener", "tuerca": "fastener",
        "taco": "fastener", "varilla": "fastener",
        "tortuga_pvc": "fastener",
        "babeta_adosar": "accessory", "babeta_empotrar": "accessory",
        "canalon": "accessory", "cumbrera": "accessory",
        "gotero_frontal": "accessory", "gotero_lateral": "accessory",
        "gotero_superior": "accessory", "vaina": "accessory",
        "embudo": "accessory", "membrana": "accessory",
        "perfil": "profile", "plegado": "profile",
        "silicona": "sealant", "cinta_butilo": "sealant",
    }
    return mapping.get(tipo, "other")


def _unit_sale(tipo: str) -> str:
    if tipo in ("perfil", "plegado", "gotero_frontal", "gotero_lateral",
                "gotero_superior", "babeta_adosar", "babeta_empotrar",
                "cumbrera", "canalon", "vaina"):
        return "ml"
    return "u"


def build_catalog_and_pricing(accessories: dict, panels_csv: list[dict]):
    """Build catalog.csv and pricing.csv from real data."""
    catalog_rows = []
    pricing_rows = []
    seen_keys = set()

    for item in accessories.get("accesorios", []):
        sku = item["sku"]
        name = item["name"]
        tipo = item.get("tipo", "other")
        compat = item.get("compatibilidad", ["UNIVERSAL"])
        espesor = item.get("espesor_mm")
        price = item.get("precio_unit_iva_inc")
        largo = item.get("largo_std_m")

        key = f"{sku}|{name}|{espesor}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        family = _family_for_compat(compat)
        system = _system_for_compat(compat)
        ptype = _product_type(tipo)
        usale = _unit_sale(tipo)
        tags = f"{tipo};{item.get('composicion', '')}"

        catalog_rows.append({
            "sku_id": sku,
            "family": family,
            "system": system,
            "product_type": ptype,
            "thickness_mm": espesor if espesor else "",
            "unit_sale": usale,
            "description": name,
            "tags": tags,
            "active": "true",
        })

        pricing_rows.append({
            "sku_id": sku,
            "currency": "USD",
            "price": price if price else "",
            "price_unit": usale,
            "iva_rate": "0.22",
            "effective_from": "2026-02-06",
            "effective_to": "",
            "notes": f"IVA incluido - {item.get('proveedor', 'BROMYROS')}",
        })

    for row in panels_csv:
        family = row.get("family", "")
        sku = row.get("sku", "")
        name = row.get("name", "")
        thickness = row.get("thickness_mm", "")
        price_iva = row.get("sale_incl_vat", "")

        if not sku or not family:
            continue

        key = f"{sku}|{name}|{thickness}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        system = "HORIZONTAL" if family in ("ISOROOF", "ISODEC") else "VERTICAL"

        catalog_rows.append({
            "sku_id": sku,
            "family": family,
            "system": system,
            "product_type": "panel",
            "thickness_mm": thickness,
            "unit_sale": "m2",
            "description": name,
            "tags": f"panel;{row.get('composition', '')}",
            "active": "true",
        })

        pricing_rows.append({
            "sku_id": sku,
            "currency": "USD",
            "price": price_iva,
            "price_unit": "m2",
            "iva_rate": "0.22",
            "effective_from": "2026-02-06",
            "effective_to": "",
            "notes": f"IVA incluido - {row.get('supplier', 'BROMYROS')}",
        })

    return catalog_rows, pricing_rows


# ── Autoportancia ────────────────────────────────────────────────

def build_autoportancia(bom_rules: dict) -> list[dict]:
    rows = []
    tablas = bom_rules.get("autoportancia", {}).get("tablas", {})
    for product, thicknesses in tablas.items():
        for thickness_str, data in thicknesses.items():
            rows.append({
                "family": product,
                "thickness_mm": int(thickness_str),
                "support_condition": "2_apoyos_simple",
                "span_m_max": data.get("luz_max_m", ""),
                "load_kPa": "",
                "weight_kg_m2": data.get("peso_kg_m2", ""),
                "slope_deg_min": "",
                "slope_deg_max": "",
                "notes": f"Pendiente min 7% para techos",
                "source": "bom_rules.json v1.0.0",
            })
    return rows


# ── Accessories Map ──────────────────────────────────────────────

def build_accessories_map(accessories: dict) -> dict:
    """Build real accessories_map.json from production accessories_catalog."""
    by_compat = accessories.get("indices", {}).get("by_compatibilidad", {})
    items = accessories.get("accesorios", [])

    def _find_sku(compat: str, tipo: str, espesor: str = None):
        indices = by_compat.get(compat, [])
        for idx in indices:
            if idx < len(items):
                item = items[idx]
                if item.get("tipo") == tipo:
                    if espesor and item.get("espesor_mm") and str(item["espesor_mm"]) != str(espesor):
                        continue
                    return item["sku"]
        return None

    rules = []

    # ISODEC EPS - HORIZONTAL
    rules.append({
        "envelope_class": "HORIZONTAL",
        "family": "ISODEC",
        "composition": "EPS",
        "accessories": {
            "gotero_frontal": _find_sku("ISODEC", "gotero_frontal", "100") or "6838",
            "gotero_lateral": _find_sku("ISODEC", "gotero_lateral", "100") or "6842",
            "babeta_adosar": _find_sku("ISODEC", "babeta_adosar") or "6828",
            "babeta_empotrar": _find_sku("ISODEC", "babeta_empotrar") or "6865",
            "cumbrera": _find_sku("ISODEC", "cumbrera") or "6847",
            "canalon": _find_sku("ISODEC", "canalon", "100") or "6801",
            "vaina": _find_sku("ISODEC", "vaina") or "6825",
            "varilla": "6805",
            "tuerca": "6805",
            "arandela_carrocero": "6805",
            "tortuga_pvc": "6805",
            "silicona": "Bromplast",
            "cinta_butilo": "C.But.",
        },
        "synonyms": {
            "gotero": "gotero_frontal",
            "gotero frontal": "gotero_frontal",
            "gotero lateral": "gotero_lateral",
            "babeta": "babeta_adosar",
            "babeta adosar": "babeta_adosar",
            "babeta empotrar": "babeta_empotrar",
            "cumbrera": "cumbrera",
            "canalon": "canalon",
            "vaina": "vaina",
            "varilla": "varilla",
            "tuerca": "tuerca",
            "arandela": "arandela_carrocero",
            "tortuga": "tortuga_pvc",
            "sellador": "silicona",
            "silicona": "silicona",
            "cinta": "cinta_butilo",
        },
    })

    # ISOROOF 3G - HORIZONTAL
    rules.append({
        "envelope_class": "HORIZONTAL",
        "family": "ISOROOF",
        "composition": "PIR",
        "accessories": {
            "gotero_frontal": _find_sku("ISOROOF", "gotero_frontal", "50") or "GFS50",
            "gotero_lateral": _find_sku("ISOROOF", "gotero_lateral", "50") or "GL50",
            "gotero_superior": _find_sku("ISOROOF", "gotero_superior", "50") or "GFSUP50",
            "babeta_adosar": _find_sku("ISOROOF", "babeta_adosar") or "BBAL",
            "babeta_empotrar": _find_sku("ISOROOF", "babeta_empotrar") or "BBAL",
            "babeta_superior": _find_sku("ISOROOF", "babeta_adosar") or "BBAS3G",
            "cumbrera": _find_sku("ISOROOF", "cumbrera") or "CUMROOF3M",
            "canalon": _find_sku("ISOROOF", "canalon", "50") or "CD50",
            "soporte_canalon": "SOPCAN3M",
            "caballete": "Cab. Roj",
            "silicona": "Bromplast",
            "cinta_butilo": "C.But.",
        },
        "synonyms": {
            "gotero": "gotero_frontal",
            "gotero frontal": "gotero_frontal",
            "gotero lateral": "gotero_lateral",
            "gotero superior": "gotero_superior",
            "babeta": "babeta_adosar",
            "babeta lateral": "babeta_adosar",
            "babeta superior": "babeta_superior",
            "cumbrera": "cumbrera",
            "canalon": "canalon",
            "soporte": "soporte_canalon",
            "caballete": "caballete",
            "sellador": "silicona",
            "silicona": "silicona",
            "cinta": "cinta_butilo",
        },
    })

    # ISOPANEL EPS - VERTICAL
    rules.append({
        "envelope_class": "VERTICAL",
        "family": "ISOPANEL",
        "composition": "EPS",
        "accessories": {
            "perfil_u": _find_sku("ISOPANEL", "perfil", "100") or "PU100MM",
            "varilla": "6805",
            "tuerca": "6805",
            "arandela_carrocero": "6805",
            "tortuga_pvc": "6805",
            "silicona": "Bromplast",
            "cinta_butilo": "C.But.",
        },
        "synonyms": {
            "perfil": "perfil_u",
            "perfil u": "perfil_u",
            "u": "perfil_u",
            "varilla": "varilla",
            "tuerca": "tuerca",
            "arandela": "arandela_carrocero",
            "tortuga": "tortuga_pvc",
            "sellador": "silicona",
            "silicona": "silicona",
            "cinta": "cinta_butilo",
        },
    })

    # ISOWALL PIR - VERTICAL
    rules.append({
        "envelope_class": "VERTICAL",
        "family": "ISOWALL",
        "composition": "PIR",
        "accessories": {
            "perfil_u": _find_sku("ISOWALL", "perfil", "50") or "PU50MM",
            "varilla": "6805",
            "tuerca": "6805",
            "arandela_carrocero": "6805",
            "tortuga_pvc": "6805",
            "silicona": "Bromplast",
            "cinta_butilo": "C.But.",
        },
        "synonyms": {
            "perfil": "perfil_u",
            "perfil u": "perfil_u",
            "u": "perfil_u",
            "varilla": "varilla",
            "tuerca": "tuerca",
            "arandela": "arandela_carrocero",
            "tortuga": "tortuga_pvc",
            "sellador": "silicona",
            "silicona": "silicona",
            "cinta": "cinta_butilo",
        },
    })

    # ISOFRIG PIR - VERTICAL
    rules.append({
        "envelope_class": "VERTICAL",
        "family": "ISOFRIG",
        "composition": "PIR",
        "accessories": {
            "perfil_u": _find_sku("ISOFRIG", "perfil") or "PU50MM",
            "varilla": "6805",
            "tuerca": "6805",
            "arandela_carrocero": "6805",
            "tortuga_pvc": "6805",
            "silicona": "Bromplast",
            "cinta_butilo": "C.But.",
        },
        "synonyms": {
            "perfil": "perfil_u",
            "perfil u": "perfil_u",
            "u": "perfil_u",
            "varilla": "varilla",
            "tuerca": "tuerca",
            "arandela": "arandela_carrocero",
            "tortuga": "tortuga_pvc",
            "sellador": "silicona",
            "silicona": "silicona",
            "cinta": "cinta_butilo",
        },
    })

    return {
        "version": "1.0.0-migrated",
        "source": "accessories_catalog.json + bom_rules.json",
        "migrated_at": "2026-02-25",
        "rules": rules,
    }


# ── Writers ──────────────────────────────────────────────────────

def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows)} rows -> {path}")


def write_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  wrote -> {path}")


# ── Main ─────────────────────────────────────────────────────────

def main():
    print("=== Migrating production data to structured kb/ ===\n")

    acc_path = ROOT / "accessories_catalog.json"
    bom_path = ROOT / "bom_rules.json"
    csv_path = ROOT / "normalized_full_cleaned.csv"

    if not acc_path.exists():
        print(f"ERROR: {acc_path} not found"); sys.exit(1)
    if not bom_path.exists():
        print(f"ERROR: {bom_path} not found"); sys.exit(1)

    accessories = load_json(acc_path)
    bom_rules = load_json(bom_path)
    panels_csv = load_csv_rows(csv_path) if csv_path.exists() else []

    # 1) Catalog + Pricing
    print("[1/4] Building catalog.csv and pricing.csv...")
    catalog_rows, pricing_rows = build_catalog_and_pricing(accessories, panels_csv)
    write_csv(
        KB_DIR / "catalog.csv",
        ["sku_id", "family", "system", "product_type", "thickness_mm",
         "unit_sale", "description", "tags", "active"],
        catalog_rows,
    )
    write_csv(
        KB_DIR / "pricing.csv",
        ["sku_id", "currency", "price", "price_unit", "iva_rate",
         "effective_from", "effective_to", "notes"],
        pricing_rows,
    )

    # 2) Autoportancia
    print("[2/4] Building autoportancia.csv...")
    auto_rows = build_autoportancia(bom_rules)
    write_csv(
        KB_DIR / "autoportancia.csv",
        ["family", "thickness_mm", "support_condition", "span_m_max",
         "load_kPa", "weight_kg_m2", "slope_deg_min", "slope_deg_max",
         "notes", "source"],
        auto_rows,
    )

    # 3) Accessories map
    print("[3/4] Building accessories_map.json...")
    acc_map = build_accessories_map(accessories)
    write_json(KB_DIR / "accessories_map.json", acc_map)

    # 4) Summary
    print(f"\n[4/4] Summary:")
    print(f"  catalog.csv:        {len(catalog_rows)} SKUs")
    print(f"  pricing.csv:        {len(pricing_rows)} price entries")
    print(f"  autoportancia.csv:  {len(auto_rows)} span records")
    print(f"  accessories_map.json: {len(acc_map['rules'])} family rules")
    print("\nMigration complete.")


if __name__ == "__main__":
    main()
