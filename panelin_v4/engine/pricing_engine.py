"""
Panelin v4.0 - Pricing Engine
================================

Deterministic pricing from KB sources only.

Rules:
    - Prices come EXCLUSIVELY from accessories_catalog.json and bromyros_pricing_master.json
    - All catalog prices include IVA 22% (NEVER add IVA on top)
    - NEVER calculate price as cost × margin
    - If price not found: explicit error, never invent
    - unit_base logic: unidad -> qty × price, ml -> qty × largo × price, m2 -> area × price
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from panelin_v4.engine.bom_engine import BOMItem, BOMResult

KB_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class PricedItem:
    tipo: str
    sku: Optional[str]
    name: Optional[str]
    quantity: int
    unit: str
    unit_price_usd: float
    subtotal_usd: float
    price_source: str = "accessories_catalog"
    price_includes_iva: bool = True

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "sku": self.sku,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price_usd": self.unit_price_usd,
            "subtotal_usd": self.subtotal_usd,
            "price_source": self.price_source,
            "price_includes_iva": self.price_includes_iva,
        }


@dataclass
class PricingResult:
    items: list[PricedItem] = field(default_factory=list)
    subtotal_panels_usd: float = 0.0
    subtotal_accessories_usd: float = 0.0
    subtotal_total_usd: float = 0.0
    iva_mode: str = "incluido"
    warnings: list[str] = field(default_factory=list)
    missing_prices: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "items": [i.to_dict() for i in self.items],
            "subtotal_panels_usd": self.subtotal_panels_usd,
            "subtotal_accessories_usd": self.subtotal_accessories_usd,
            "subtotal_total_usd": self.subtotal_total_usd,
            "iva_mode": self.iva_mode,
            "warnings": self.warnings,
            "missing_prices": self.missing_prices,
        }


_ACCESSORIES_CACHE: Optional[dict] = None
_PRICING_CACHE: Optional[list] = None


def _load_accessories() -> dict:
    global _ACCESSORIES_CACHE
    if _ACCESSORIES_CACHE is None:
        with open(KB_ROOT / "accessories_catalog.json", encoding="utf-8") as f:
            _ACCESSORIES_CACHE = json.load(f)
    return _ACCESSORIES_CACHE


def _load_pricing_master() -> list:
    global _PRICING_CACHE
    if _PRICING_CACHE is None:
        with open(KB_ROOT / "bromyros_pricing_master.json", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        if isinstance(data, dict):
            products = data.get("products", data.get("items", []))
            if isinstance(products, dict):
                items = []
                for k, v in products.items():
                    if isinstance(v, dict):
                        v["_key"] = k
                        items.append(v)
                    elif isinstance(v, list):
                        items.extend(v)
                products = items
            _PRICING_CACHE = products
        elif isinstance(data, list):
            _PRICING_CACHE = data
        else:
            _PRICING_CACHE = []
    return _PRICING_CACHE


def _round_usd(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _find_accessory_price(sku: Optional[str], tipo: str) -> Optional[float]:
    """Find accessory price from catalog by SKU or type."""
    catalog = _load_accessories()
    accesorios = catalog.get("accesorios", [])

    if sku:
        for acc in accesorios:
            if str(acc.get("sku", "")) == str(sku):
                return acc.get("precio_unit_iva_inc")

    for acc in accesorios:
        if acc.get("tipo") == tipo:
            return acc.get("precio_unit_iva_inc")

    return None


def _find_panel_price_m2(familia: str, sub_familia: str, thickness_mm: int) -> Optional[float]:
    """Find panel price per m2 from pricing master."""
    products = _load_pricing_master()

    norm_familia = familia.upper().replace("_", "").replace("-", "")
    norm_sub = sub_familia.upper() if sub_familia else ""

    for product in products:
        if not isinstance(product, dict):
            continue

        sku = str(product.get("sku", product.get("SKU", ""))).upper().replace("_", "").replace("-", "")
        name = str(product.get("nombre", product.get("name", ""))).upper()
        fam = str(product.get("familia", product.get("family", ""))).upper()

        thickness = product.get("espesor_mm", product.get("thickness"))
        if thickness is None:
            specs = product.get("specifications", {})
            if isinstance(specs, dict):
                thickness = specs.get("thickness_mm", specs.get("espesor_mm"))

        if thickness is not None:
            try:
                if int(float(thickness)) != thickness_mm:
                    continue
            except (ValueError, TypeError):
                continue
        else:
            continue

        if norm_familia in sku or norm_familia in name or norm_familia in fam:
            pricing = product.get("pricing", {})
            if isinstance(pricing, dict):
                price = pricing.get("sale_iva_inc", pricing.get("web_iva_inc"))
                if price:
                    return float(price)

    return None


def calculate_pricing(
    bom: BOMResult,
    familia: str,
    sub_familia: str,
    thickness_mm: int,
    panel_area_m2: Optional[float] = None,
    iva_mode: str = "incluido",
) -> PricingResult:
    """Calculate pricing for all BOM items.

    Prices come exclusively from KB files. Never invents prices.
    """
    result = PricingResult(iva_mode=iva_mode)

    for bom_item in bom.items:
        if bom_item.tipo == "panel":
            price_m2 = _find_panel_price_m2(familia, sub_familia, thickness_mm)
            if price_m2 is not None:
                area = panel_area_m2 or bom.area_m2
                subtotal = _round_usd(price_m2 * area)
                priced = PricedItem(
                    tipo="panel",
                    sku=bom_item.referencia,
                    name=f"{familia} {sub_familia} {thickness_mm}mm",
                    quantity=bom.panel_count,
                    unit="m2",
                    unit_price_usd=price_m2,
                    subtotal_usd=subtotal,
                    price_source="bromyros_pricing_master",
                )
                result.items.append(priced)
                result.subtotal_panels_usd += subtotal
            else:
                result.missing_prices.append(
                    f"Panel {familia} {sub_familia} {thickness_mm}mm: price not found in KB"
                )
        else:
            price = _find_accessory_price(bom_item.sku, bom_item.tipo)
            if price is not None:
                subtotal = _round_usd(price * bom_item.quantity)
                priced = PricedItem(
                    tipo=bom_item.tipo,
                    sku=bom_item.sku,
                    name=bom_item.name,
                    quantity=bom_item.quantity,
                    unit=bom_item.unit,
                    unit_price_usd=price,
                    subtotal_usd=subtotal,
                    price_source="accessories_catalog",
                )
                result.items.append(priced)
                result.subtotal_accessories_usd += subtotal
            else:
                result.missing_prices.append(
                    f"{bom_item.tipo} (SKU: {bom_item.sku}): price not found in accessories_catalog"
                )

    result.subtotal_panels_usd = _round_usd(result.subtotal_panels_usd)
    result.subtotal_accessories_usd = _round_usd(result.subtotal_accessories_usd)
    result.subtotal_total_usd = _round_usd(
        result.subtotal_panels_usd + result.subtotal_accessories_usd
    )

    if result.missing_prices:
        result.warnings.append(
            f"{len(result.missing_prices)} item(s) could not be priced from KB"
        )

    return result
