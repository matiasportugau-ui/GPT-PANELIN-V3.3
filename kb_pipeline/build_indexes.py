#!/usr/bin/env python3
"""Build lightweight MCP lookup artifacts with provenance manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT / "artifacts"
HOT_DIR = ARTIFACTS_DIR / "hot"


@dataclass(frozen=True)
class SourceConfig:
    source_file: str
    output_file: str


SOURCES = [
    SourceConfig("shopify_catalog_v1.json", "shopify_catalog_v1.hot.json"),
    SourceConfig("bromyros_pricing_master.json", "bromyros_pricing_master.hot.json"),
    SourceConfig("bromyros_pricing_gpt_optimized.json", "bromyros_pricing_gpt_optimized.hot.json"),
]

INVALID_SKUS = {"subido con éxito", "subido con exito", "n/a", "na", "none"}

REQUIRED_HOT_FIELDS = [
    "sku",
    "title",
    "category",
    "price",
    "availability",
    "source_file",
    "source_key",
    "checksum",
]


def _sha256_json(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_shopify(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    products = payload.get("products_by_handle", {})

    records: list[dict[str, Any]] = []
    for handle, product in products.items():
        variants = product.get("variants") or [{}]
        for variant_index, variant in enumerate(variants):
            sku = (variant.get("sku") or "").strip()
            if not sku or sku.lower() in INVALID_SKUS:
                continue

            source_key = f"products_by_handle.{handle}.variants[{variant_index}]"
            source_node = {
                "handle": handle,
                "product": product,
                "variant": variant,
            }
            record = {
                "sku": sku,
                "title": product.get("title") or "unknown",
                "category": product.get("product_category") or product.get("type") or "unknown",
                "price": variant.get("price") if variant.get("price") not in (None, "") else "unknown",
                "availability": (
                    variant.get("available")
                    if variant.get("available") is not None
                    else ("available" if product.get("published") else "unknown")
                ),
                "source_file": path.name,
                "source_key": source_key,
                "checksum": _sha256_json(source_node),
            }
            records.append(record)

    return records


def _parse_pricing(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    products = payload.get("products")
    products_root = "products"

    if products is None and isinstance(payload.get("data"), dict):
        products = payload["data"].get("products", [])
        products_root = "data.products"

    if products is None:
        raise ValueError(f"Unsupported pricing schema in {path.name}")

    records: list[dict[str, Any]] = []
    for index, product in enumerate(products):
        sku = (product.get("sku") or "").strip()
        if not sku:
            continue

        pricing = product.get("pricing", {})
        source_key = f"{products_root}[{index}]"
        record = {
            "sku": sku,
            "title": product.get("name") or "unknown",
            "category": product.get("familia") or product.get("sub_familia") or "unknown",
            "price": pricing.get("web_iva_inc") if pricing.get("web_iva_inc") not in (None, "") else "unknown",
            "availability": "unknown",
            "source_file": path.name,
            "source_key": source_key,
            "checksum": _sha256_json(product),
        }
        records.append(record)

    return records


def _validate(records_by_source: dict[str, list[dict[str, Any]]]) -> None:
    issues: list[str] = []

    for source_name, records in records_by_source.items():
        seen_skus: dict[str, int] = {}
        seen_source_keys: set[str] = set()

        for idx, record in enumerate(records):
            for field in REQUIRED_HOT_FIELDS:
                value = record.get(field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    issues.append(f"{source_name}[{idx}] missing required field '{field}'")

            sku = record["sku"]
            seen_skus[sku] = seen_skus.get(sku, 0) + 1

            source_key = record["source_key"]
            if source_key in seen_source_keys:
                issues.append(f"{source_name} duplicate source_key '{source_key}'")
            seen_source_keys.add(source_key)

        for sku, count in seen_skus.items():
            if count > 1:
                issues.append(f"{source_name} duplicated sku '{sku}' ({count} records)")

    cross_catalog_source_refs: dict[tuple[str, str], str] = {}
    for source_name, records in records_by_source.items():
        for record in records:
            key = (record["source_key"], record["checksum"])
            if key in cross_catalog_source_refs and cross_catalog_source_refs[key] != source_name:
                issues.append(
                    "duplicated immutable source reference across catalogs: "
                    f"{key[0]} checksum={key[1][:12]}..., "
                    f"{cross_catalog_source_refs[key]} and {source_name}"
                )
            cross_catalog_source_refs[key] = source_name

    if issues:
        message = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"Validation failed:\n{message}")


def _build_source_manifest(records_by_source: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    sources = []
    for source_name, records in records_by_source.items():
        source_path = ROOT / source_name
        source_payload = _load_json(source_path)
        unique_skus = len({record["sku"] for record in records})
        sources.append(
            {
                "source_file": source_name,
                "source_file_sha256": _sha256_json(source_payload),
                "indexed_rows": len(records),
                "unique_skus": unique_skus,
                "required_fields": REQUIRED_HOT_FIELDS,
                "hot_artifact": f"hot/{Path(source_name).stem}.hot.json",
            }
        )

    return {
        "version": 1,
        "generator": "kb_pipeline/build_indexes.py",
        "sources": sources,
    }


def main() -> None:
    HOT_DIR.mkdir(parents=True, exist_ok=True)

    records_by_source: dict[str, list[dict[str, Any]]] = {}
    for source in SOURCES:
        source_path = ROOT / source.source_file
        if "shopify_catalog" in source.source_file:
            records = _parse_shopify(source_path)
        else:
            records = _parse_pricing(source_path)
        records_by_source[source.source_file] = records

    _validate(records_by_source)

    for source in SOURCES:
        output_path = HOT_DIR / source.output_file
        output_records = records_by_source[source.source_file]
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(output_records, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    manifest = _build_source_manifest(records_by_source)
    manifest_path = ARTIFACTS_DIR / "source_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print("Built artifacts:")
    for source in SOURCES:
        output_path = HOT_DIR / source.output_file
        print(f"- {output_path.relative_to(ROOT)} ({output_path.stat().st_size} bytes)")
    print(f"- {manifest_path.relative_to(ROOT)} ({manifest_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
