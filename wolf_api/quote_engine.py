"""
Panelin Wolf API v2 — Smart Quote Engine
==========================================

POST /v2/smart_quote — Deterministic BOM + pricing pipeline.

Given a panel product_id and dimensions, calculates the complete
Bill of Materials including:
  - Panels (area-based)
  - Fixings (16 per m² — varillas, tuercas, arandelas)
  - Sealant (1 tube per 10 m²)
  - Flashings (perimeter-based — goteros, babetas)

Applies:
  - Volume discounts: 100-500m²=5%, 500-1000m²=10%, >1000m²=15%
  - Manual discount (0-30%)
  - Waste factor: 7%
  - IVA: 22% (already included in catalog prices)

Returns a complete SmartQuoteResponse with all line items.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Security

from wolf_api.schemas_v2 import LineItem, SmartQuoteRequest, SmartQuoteResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["Smart Quote Engine v2"])

# Reference to the global CATALOG — set by main.py at startup
_CATALOG: dict = {}

# ─── Default prices for BOM items when catalog doesn't have exact SKU ───
# These are real prices from the BROMYROS catalog (IVA included)
DEFAULT_FIXING_PRICE = 0.60       # Generic fixing unit (caballete/arandela avg)
DEFAULT_SEALANT_PRICE = 11.58     # Bromplast silicona
DEFAULT_BUTILO_PRICE = 18.17      # Cinta butilo
DEFAULT_FLASHING_PRICE = 25.00    # Generic gotero/babeta avg
DEFAULT_CUMBRERA_PRICE = 28.75    # Cumbrera perfil

# ─── BOM ratios ───
FIXINGS_PER_M2 = 16               # Fixation points per m²
SEALANT_TUBES_PER_M2 = 0.10       # 1 tube per 10 m²
FLASHING_LENGTH_M = 3.0           # Standard profile length in meters

# ─── Installation time estimate ───
INSTALL_HOURS_PER_M2_TECHO = 0.35  # ~3 m²/hour for roof
INSTALL_HOURS_PER_M2_PARED = 0.25  # ~4 m²/hour for wall

# ─── Volume discount tiers ───
VOLUME_DISCOUNT_TIERS = [
    (1000, 0.15),   # > 1000 m² → 15%
    (500, 0.10),    # 500-1000 m² → 10%
    (100, 0.05),    # 100-500 m² → 5%
]

# ─── Waste factor ───
WASTE_FACTOR = 0.07  # 7%


def set_catalog(catalog: dict) -> None:
    """Called by main.py to inject the loaded CATALOG."""
    global _CATALOG
    _CATALOG = catalog


def _get_volume_discount(area_m2: float) -> float:
    """Calculate automatic volume discount based on total area."""
    for threshold, discount in VOLUME_DISCOUNT_TIERS:
        if area_m2 >= threshold:
            return discount
    return 0.0


def _find_best_fixing(catalog: dict, panel_familia: str) -> tuple[str, str, float]:
    """Find the best fixing product for the panel family."""
    # Search for family-specific fixings
    for pid, p in catalog.items():
        tipo = p.get("tipo", "")
        if "Fijacion" not in tipo and "Anclaje" not in tipo:
            continue
        pfam = p.get("familia", "")
        if panel_familia.upper() in pfam.upper():
            return pid, p.get("name", pid), float(p.get("price_usd", DEFAULT_FIXING_PRICE))

    # Fallback to generic fixing
    for pid, p in catalog.items():
        tipo = p.get("tipo", "")
        if "Fijacion" in tipo or "Anclaje" in tipo:
            return pid, p.get("name", pid), float(p.get("price_usd", DEFAULT_FIXING_PRICE))

    return "FIX-GEN", "Fijación genérica", DEFAULT_FIXING_PRICE


def _find_sealant(catalog: dict) -> tuple[str, str, float]:
    """Find silicone sealant product."""
    for pid, p in catalog.items():
        if "silicona" in p.get("name", "").lower() or "bromplast" in pid.lower():
            return pid, p.get("name", pid), float(p.get("price_usd", DEFAULT_SEALANT_PRICE))
    return "Bromplast", "Bromplast 8 - Silicona Neutra", DEFAULT_SEALANT_PRICE


def _find_butilo(catalog: dict) -> tuple[str, str, float]:
    """Find butyl tape product."""
    for pid, p in catalog.items():
        if "butilo" in p.get("name", "").lower() or pid == "C.But.":
            return pid, p.get("name", pid), float(p.get("price_usd", DEFAULT_BUTILO_PRICE))
    return "C.But.", "Cinta Butilo 2mm x 15mm x 22.5m", DEFAULT_BUTILO_PRICE


def _find_flashings(
    catalog: dict, panel_familia: str, thickness_mm: Optional[float], perimeter_m: float
) -> list[LineItem]:
    """Find and calculate flashing items (goteros, babetas) for perimeter."""
    items: list[LineItem] = []

    # Gotero frontal — top/bottom edges (width dimension × 2)
    gotero_frontal = None
    for pid, p in catalog.items():
        if "Perfileria" not in p.get("tipo", "") and "Gotero" not in p.get("tipo", ""):
            continue
        name_lower = p.get("name", "").lower()
        if "gotero" not in name_lower or "frontal" not in name_lower:
            continue
        p_thick = p.get("thickness_mm")
        if thickness_mm and p_thick and abs(float(p_thick) - thickness_mm) < 5:
            gotero_frontal = (pid, p)
            break
    # Fallback: any gotero frontal
    if not gotero_frontal:
        for pid, p in catalog.items():
            name_lower = p.get("name", "").lower()
            if "gotero" in name_lower and "frontal" in name_lower:
                gotero_frontal = (pid, p)
                break

    # Gotero lateral — side edges (length dimension × 2)
    gotero_lateral = None
    for pid, p in catalog.items():
        if "Perfileria" not in p.get("tipo", "") and "Gotero" not in p.get("tipo", ""):
            continue
        name_lower = p.get("name", "").lower()
        if "gotero" not in name_lower or "lateral" not in name_lower:
            continue
        p_thick = p.get("thickness_mm")
        if thickness_mm and p_thick and abs(float(p_thick) - thickness_mm) < 5:
            gotero_lateral = (pid, p)
            break
    if not gotero_lateral:
        for pid, p in catalog.items():
            name_lower = p.get("name", "").lower()
            if "gotero" in name_lower and "lateral" in name_lower:
                gotero_lateral = (pid, p)
                break

    # Calculate quantities based on perimeter
    half_perimeter = perimeter_m / 2  # Split between frontal and lateral

    if gotero_frontal:
        pid, p = gotero_frontal
        price = float(p.get("price_usd", DEFAULT_FLASHING_PRICE))
        # Each piece covers ~3m
        qty = math.ceil(half_perimeter / FLASHING_LENGTH_M)
        items.append(LineItem(
            product_id=pid,
            name=p.get("name", "Gotero Frontal"),
            category="flashing",
            quantity=qty,
            unit="unid",
            unit_price=round(price, 2),
            subtotal=round(qty * price, 2),
        ))

    if gotero_lateral:
        pid, p = gotero_lateral
        price = float(p.get("price_usd", DEFAULT_FLASHING_PRICE))
        qty = math.ceil(half_perimeter / FLASHING_LENGTH_M)
        items.append(LineItem(
            product_id=pid,
            name=p.get("name", "Gotero Lateral"),
            category="flashing",
            quantity=qty,
            unit="unid",
            unit_price=round(price, 2),
            subtotal=round(qty * price, 2),
        ))

    # If no flashings found, add generic
    if not items:
        qty = math.ceil(perimeter_m / FLASHING_LENGTH_M)
        items.append(LineItem(
            product_id="FLASH-GEN",
            name="Perfil/Gotero perimetral genérico (3m)",
            category="flashing",
            quantity=qty,
            unit="unid",
            unit_price=DEFAULT_FLASHING_PRICE,
            subtotal=round(qty * DEFAULT_FLASHING_PRICE, 2),
        ))

    return items


def calculate_smart_quote(req: SmartQuoteRequest) -> SmartQuoteResponse:
    """Execute the complete quotation pipeline.

    Deterministic: same input → same output. No LLM inference.
    """
    catalog = _CATALOG
    if not catalog:
        raise HTTPException(503, "Catalog not loaded. API not ready.")

    # ── 1. Resolve main panel product ──
    product = catalog.get(req.product_id)
    if not product:
        raise HTTPException(
            404,
            f"Product not found: {req.product_id}. "
            f"Use POST /find_products to search, or GET /product_catalog to browse.",
        )

    panel_price = float(product.get("price_usd", 0))
    if panel_price <= 0:
        raise HTTPException(400, f"Product {req.product_id} has no valid price.")

    panel_name = product.get("name", req.product_id)
    panel_familia = product.get("familia", "")
    panel_thickness = product.get("thickness_mm")
    panel_unit = product.get("unit", "m2")

    # ── 2. Calculate geometry ──
    area_m2 = req.length_m * req.width_m * req.quantity
    perimeter_m = 2 * (req.length_m + req.width_m) * req.quantity

    # ── 3. Build line items ──
    line_items: list[LineItem] = []
    notes: list[str] = []

    # Panel
    panel_qty_m2 = math.ceil(area_m2)  # Round up to full m²
    line_items.append(LineItem(
        product_id=req.product_id,
        name=panel_name,
        category="panel",
        quantity=panel_qty_m2,
        unit=panel_unit,
        unit_price=round(panel_price, 2),
        subtotal=round(panel_qty_m2 * panel_price, 2),
    ))

    # Fixings (16 per m²)
    if req.include_fixings:
        fix_pid, fix_name, fix_price = _find_best_fixing(catalog, panel_familia)
        fix_qty = math.ceil(area_m2 * FIXINGS_PER_M2)
        line_items.append(LineItem(
            product_id=fix_pid,
            name=fix_name,
            category="fixing",
            quantity=fix_qty,
            unit="unid",
            unit_price=round(fix_price, 2),
            subtotal=round(fix_qty * fix_price, 2),
        ))

    # Sealant (1 tube per 10 m²)
    if req.include_sealant:
        seal_pid, seal_name, seal_price = _find_sealant(catalog)
        seal_qty = math.ceil(area_m2 * SEALANT_TUBES_PER_M2)
        line_items.append(LineItem(
            product_id=seal_pid,
            name=seal_name,
            category="sealant",
            quantity=max(1, seal_qty),
            unit="tubo",
            unit_price=round(seal_price, 2),
            subtotal=round(max(1, seal_qty) * seal_price, 2),
        ))

        # Butyl tape
        but_pid, but_name, but_price = _find_butilo(catalog)
        but_qty = math.ceil(perimeter_m / 22.5)  # 1 roll covers 22.5m
        if but_qty > 0:
            line_items.append(LineItem(
                product_id=but_pid,
                name=but_name,
                category="sealant",
                quantity=max(1, but_qty),
                unit="rollo",
                unit_price=round(but_price, 2),
                subtotal=round(max(1, but_qty) * but_price, 2),
            ))

    # Flashings (perimeter-based)
    if req.include_accessories:
        flashing_items = _find_flashings(catalog, panel_familia, panel_thickness, perimeter_m)
        line_items.extend(flashing_items)

    # ── 4. Calculate subtotal ──
    subtotal = sum(item.subtotal for item in line_items)

    # ── 5. Volume discount ──
    vol_disc_pct = _get_volume_discount(area_m2)
    vol_disc_amt = round(subtotal * vol_disc_pct, 2)

    # ── 6. Manual discount ──
    man_disc_pct = req.discount_percent / 100.0
    man_disc_amt = round(subtotal * man_disc_pct, 2)

    # ── 7. Total discount ──
    total_discount = round(vol_disc_amt + man_disc_amt, 2)
    after_discount = round(subtotal - total_discount, 2)

    # ── 8. Waste factor (7%) ──
    waste_cost = round(after_discount * WASTE_FACTOR, 2)

    # ── 9. Total before tax adjustment ──
    total_before_tax = round(after_discount + waste_cost, 2)

    # ── 10. IVA handling ──
    # Catalog prices INCLUDE IVA 22%. So total_before_tax already has IVA.
    # If user wants WITHOUT tax, we remove IVA.
    iva_rate = 0.22
    if req.include_tax:
        total = total_before_tax
        iva_amount = round(total_before_tax - total_before_tax / (1 + iva_rate), 2)
    else:
        total = round(total_before_tax / (1 + iva_rate), 2)
        iva_amount = round(total_before_tax - total, 2)

    # ── 11. Installation estimate ──
    hours_per_m2 = (
        INSTALL_HOURS_PER_M2_TECHO
        if req.installation_type == "techo"
        else INSTALL_HOURS_PER_M2_PARED
    )
    install_hours = round(area_m2 * hours_per_m2, 1)

    # ── 12. Notes ──
    if vol_disc_pct > 0:
        notes.append(
            f"Descuento por volumen aplicado: {vol_disc_pct*100:.0f}% "
            f"(área total {area_m2:.0f} m²)"
        )
    if req.discount_percent > 0:
        notes.append(f"Descuento manual aplicado: {req.discount_percent:.1f}%")

    notes.append(
        f"Factor de desperdicio: {WASTE_FACTOR*100:.0f}% incluido (USD {waste_cost:.2f})"
    )
    notes.append(
        "Precios con IVA 22% incluido. BMC Uruguay vende materiales y brinda "
        "asesoramiento técnico; no realiza instalaciones."
    )
    notes.append(
        f"Horas estimadas de instalación: {install_hours:.1f}h "
        f"(referencia — consultar con instalador profesional)"
    )

    # ── 13. Build response ──
    return SmartQuoteResponse(
        quote_id=SmartQuoteResponse.generate_quote_id(),
        product_id=req.product_id,
        product_name=panel_name,
        area_m2=round(area_m2, 2),
        quantity=req.quantity,
        installation_type=req.installation_type,
        line_items=line_items,
        subtotal=round(subtotal, 2),
        volume_discount_percent=round(vol_disc_pct * 100, 1),
        volume_discount_amount=vol_disc_amt,
        manual_discount_percent=req.discount_percent,
        manual_discount_amount=man_disc_amt,
        discount_amount=total_discount,
        after_discount=after_discount,
        waste_factor_percent=WASTE_FACTOR * 100,
        waste_cost=waste_cost,
        iva_rate=iva_rate,
        iva_included=req.include_tax,
        iva_amount=iva_amount,
        total=round(total, 2),
        estimated_install_hours=install_hours,
        valid_until=SmartQuoteResponse.calculate_valid_until(),
        notes=notes,
    )


# ─── FastAPI Route ───

@router.post(
    "/smart_quote",
    response_model=SmartQuoteResponse,
    summary="Smart Quote — Complete BOM + Pricing Pipeline",
    description=(
        "Deterministic quotation engine. Given a panel product and dimensions, "
        "calculates the complete BOM (panels + fixings + sealant + flashings), "
        "applies volume discounts, waste factor, and returns a fully priced quote. "
        "NEVER let the LLM calculate — always use this endpoint."
    ),
)
async def smart_quote(req: SmartQuoteRequest):
    """Requires X-API-Key header (enforced by main.py dependency)."""
    return calculate_smart_quote(req)
