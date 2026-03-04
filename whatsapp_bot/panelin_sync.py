"""Panelin / Wolf API integration for BMC Uruguay product knowledge base.

Reads the existing JSON knowledge base files (pricing, BOM rules,
accessories, core KB) and transforms them into embedding-optimized
text documents for OpenAI Vector Store indexing.

Also provides lead/customer persistence via the Wolf API endpoints
already deployed at https://panelin-api-*.run.app.

Data sources:
- bromyros_pricing_master.json: 96 products with SKU, family, pricing
- BMC_Base_Conocimiento_GPT-2.json: Institutional info, product specs, BOM rules
- accessories_catalog.json: Accessories, fixings, sealants
- bom_rules.json: Bill of Materials calculation rules by construction system
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class Product:
    """Parsed product from BMC Uruguay knowledge base."""

    sku: str = ""
    name: str = ""
    family: str = ""
    sub_family: str = ""
    product_type: str = "Panel"
    core: str = ""  # EPS, PIR, Lana de Roca
    thickness_mm: int = 0
    price_usd: float = 0.0
    price_with_iva: float = 0.0
    unit: str = "m²"
    width_m: float = 0.0
    autoportancia_m: float = 0.0
    description: str = ""
    extra_attrs: dict = field(default_factory=dict)


def load_products_from_pricing(pricing_path: str) -> list[Product]:
    """Load products from bromyros_pricing_master.json.

    Parses the hierarchical pricing structure into flat Product objects
    suitable for embedding and vector store indexing.

    Args:
        pricing_path: Path to bromyros_pricing_master.json.

    Returns:
        List of Product objects.
    """
    path = Path(pricing_path)
    if not path.exists():
        logger.error("Pricing file not found: %s", pricing_path)
        return []

    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to parse pricing file: %s", pricing_path)
        return []

    products: list[Product] = []
    data = raw.get("data", raw)

    # Parse products from the nested structure
    product_list = data.get("products", [])
    if isinstance(product_list, list):
        for item in product_list:
            products.append(_parse_product_entry(item))
    elif isinstance(product_list, dict):
        for sku, item in product_list.items():
            if isinstance(item, dict):
                item.setdefault("sku", sku)
                products.append(_parse_product_entry(item))

    # Also parse from indices.by_sku if products list is empty
    if not products:
        indices = data.get("indices", {})
        by_sku = indices.get("by_sku", {})
        for sku, info in by_sku.items():
            if isinstance(info, dict):
                info["sku"] = sku
                products.append(_parse_product_entry(info))

    logger.info("Loaded %d products from %s", len(products), pricing_path)
    return products


def load_products_from_kb(kb_path: str) -> list[Product]:
    """Load products from BMC_Base_Conocimiento_GPT-2.json.

    Extracts the 'products' section which contains detailed
    specifications per product family (ISODEC_EPS, ISOPANEL_PIR, etc.).

    Args:
        kb_path: Path to BMC_Base_Conocimiento_GPT-2.json.

    Returns:
        List of Product objects with full specifications.
    """
    path = Path(kb_path)
    if not path.exists():
        logger.error("KB file not found: %s", kb_path)
        return []

    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("Failed to parse KB file: %s", kb_path)
        return []

    products: list[Product] = []
    product_families = raw.get("products", {})

    for family_key, family_data in product_families.items():
        if not isinstance(family_data, dict):
            continue

        name = family_data.get("nombre_comercial", family_key)
        prod_type = family_data.get("tipo", "")
        width = family_data.get("ancho_util", 0)
        fix_system = family_data.get("sistema_fijacion", "")

        # Parse each thickness variant
        espesores = family_data.get("espesores", {})
        for thickness_str, specs in espesores.items():
            if not isinstance(specs, dict):
                continue
            try:
                thickness = int(thickness_str)
            except (ValueError, TypeError):
                thickness = 0

            sku = f"{family_key}_{thickness}"
            price = specs.get("precio", 0.0)
            auto = specs.get("autoportancia", 0.0)

            products.append(Product(
                sku=sku,
                name=f"{name} {thickness}mm",
                family=family_key,
                sub_family=family_data.get("ignifugo", ""),
                product_type=prod_type,
                core=family_key.split("_")[-1] if "_" in family_key else "",
                thickness_mm=thickness,
                price_usd=float(price),
                price_with_iva=round(float(price) * 1.22, 2),
                unit="m²",
                width_m=float(width) if width else 0.0,
                autoportancia_m=float(auto) if auto else 0.0,
                description=f"{name} espesor {thickness}mm, "
                            f"autoportancia {auto}m, "
                            f"fijación {fix_system}",
                extra_attrs=specs,
            ))

    logger.info("Loaded %d product variants from %s", len(products), kb_path)
    return products


def _parse_product_entry(item: dict) -> Product:
    """Parse a single product entry from pricing JSON."""
    sku = str(item.get("sku", item.get("SKU", item.get("codigo", ""))))
    family = str(item.get("familia", item.get("family", item.get("_key", ""))))

    # Try to extract thickness from SKU (e.g., IROOF100 → 100)
    thickness = 0
    for part in sku.split("-"):
        digits = "".join(c for c in part if c.isdigit())
        if digits:
            try:
                thickness = int(digits)
            except ValueError:
                pass
            break

    price = float(item.get("precio_venta", item.get("price", item.get("precio", 0))))

    return Product(
        sku=sku,
        name=item.get("nombre", item.get("name", sku)),
        family=family,
        sub_family=str(item.get("sub_familia", item.get("sub_family", ""))),
        product_type=str(item.get("tipo", item.get("type", "Panel"))),
        thickness_mm=thickness,
        price_usd=price,
        price_with_iva=round(price * 1.22, 2),
        unit=str(item.get("unidad", item.get("unit", "m²"))),
    )


def transform_products_to_documents(
    products: list[Product],
) -> list[tuple[str, str]]:
    """Convert products to embedding-optimized text documents.

    Each document uses ~150-250 tokens in structured Markdown.
    Optimized for the BMC Uruguay product domain with panel-specific
    attributes (espesor, autoportancia, IVA 22%).

    Returns:
        List of (filename, content) tuples.
    """
    documents: list[tuple[str, str]] = []
    for prod in products:
        content = (
            f"# Producto: {prod.name}\n"
            f"SKU: {prod.sku}\n"
            f"Familia: {prod.family}\n"
            f"Tipo: {prod.product_type}\n"
        )
        if prod.thickness_mm:
            content += f"Espesor: {prod.thickness_mm} mm\n"
        if prod.price_usd:
            content += (
                f"Precio: USD {prod.price_usd:.2f}/{prod.unit} "
                f"(con IVA 22%: USD {prod.price_with_iva:.2f}/{prod.unit})\n"
            )
        if prod.width_m:
            content += f"Ancho útil: {prod.width_m} m\n"
        if prod.autoportancia_m:
            content += f"Autoportancia: {prod.autoportancia_m} m\n"
        if prod.core:
            content += f"Núcleo: {prod.core}\n"
        if prod.description:
            content += f"\n{prod.description}\n"

        filename = f"product_{prod.sku}.txt"
        documents.append((filename, content))

    return documents


async def save_customer_to_wolf_api(
    wolf_api_url: str,
    wolf_api_key: str,
    customer_data: dict,
) -> str | None:
    """Save a qualified lead/customer to the Wolf API KB.

    Posts to the existing /kb/customers endpoint on the Panelin
    Wolf API, which persists to GCS as JSONL.

    Args:
        wolf_api_url: Wolf API base URL.
        wolf_api_key: X-API-Key for authentication.
        customer_data: Dict with keys: name, phone, address,
                       city, department, notes.

    Returns:
        Customer ID from Wolf API on success, None on failure.
    """

    async def _do_save() -> str | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{wolf_api_url}/kb/customers",
                json=customer_data,
                headers={"X-API-Key": wolf_api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("customer_id")

    try:
        return await retry_with_backoff(_do_save, max_retries=2)
    except Exception:
        logger.exception("Failed to save customer to Wolf API")
        return None


async def persist_conversation_to_wolf_api(
    wolf_api_url: str,
    wolf_api_key: str,
    conversation_data: dict,
) -> bool:
    """Persist a conversation summary to the Wolf API KB.

    Posts to /kb/conversations for analytics and self-learning.

    Args:
        wolf_api_url: Wolf API base URL.
        wolf_api_key: X-API-Key for authentication.
        conversation_data: Dict with client_id, summary, products_discussed.

    Returns:
        True on success, False on failure.
    """

    async def _do_persist() -> bool:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{wolf_api_url}/kb/conversations",
                json=conversation_data,
                headers={"X-API-Key": wolf_api_key},
            )
            resp.raise_for_status()
            return True

    try:
        return await retry_with_backoff(_do_persist, max_retries=2)
    except Exception:
        logger.exception("Failed to persist conversation to Wolf API")
        return False
