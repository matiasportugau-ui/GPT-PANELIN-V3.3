"""
Panelin v5.0 — Price Guardrail
==================================

Output guardrail that validates the agent never invents prices.
Checks that any price mentioned in the response exists in the KB.

This is a critical safety guardrail: BMC's pricing must come
exclusively from bromyros_pricing_master.json and accessories_catalog.json.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KNOWN_PRICES_CACHE: Optional[set[float]] = None


def _load_known_prices() -> set[float]:
    """Load all valid prices from KB files into a set for fast lookup."""
    global _KNOWN_PRICES_CACHE
    if _KNOWN_PRICES_CACHE is not None:
        return _KNOWN_PRICES_CACHE

    prices: set[float] = set()
    kb_root = Path(__file__).resolve().parent.parent.parent

    pricing_path = kb_root / "bromyros_pricing_master.json"
    if pricing_path.exists():
        try:
            with open(pricing_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            products = data if isinstance(data, list) else data.get("products", [])
            if isinstance(products, dict):
                products = list(products.values())
            for product in products:
                if not isinstance(product, dict):
                    continue
                pricing = product.get("pricing", {})
                if isinstance(pricing, dict):
                    for key in ("sale_iva_inc", "web_iva_inc", "base", "sale"):
                        val = pricing.get(key)
                        if val is not None:
                            try:
                                prices.add(round(float(val), 2))
                            except (ValueError, TypeError):
                                pass
        except Exception as e:
            logger.warning("Could not load pricing master: %s", e)

    acc_path = kb_root / "accessories_catalog.json"
    if acc_path.exists():
        try:
            with open(acc_path, encoding="utf-8") as f:
                acc_data = json.load(f)
            for acc in acc_data.get("accesorios", []):
                val = acc.get("precio_unit_iva_inc")
                if val is not None:
                    try:
                        prices.add(round(float(val), 2))
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.warning("Could not load accessories catalog: %s", e)

    _KNOWN_PRICES_CACHE = prices
    logger.info("Loaded %d known prices for guardrail", len(prices))
    return prices


_PRICE_PATTERN = re.compile(r"\$\s*(\d+[.,]\d{2})")
_UNIT_PRICE_PATTERN = re.compile(r"(?:USD|usd|\$)\s*(\d+[.,]\d{1,2})\s*/?\s*(?:m[²2]|unid|ml|rollo|tubo)")


def validate_prices_in_response(response_text: str) -> dict:
    """Validate that prices in the agent's response exist in the KB.

    Args:
        response_text: The agent's response text to validate.

    Returns:
        Dict with validation result:
            - valid: bool
            - suspicious_prices: list of prices not found in KB
            - checked_count: number of prices checked
    """
    known_prices = _load_known_prices()

    all_price_matches = _PRICE_PATTERN.findall(response_text)
    unit_price_matches = _UNIT_PRICE_PATTERN.findall(response_text)

    all_mentioned = set()
    for match in all_price_matches + unit_price_matches:
        try:
            price = round(float(match.replace(",", ".")), 2)
            if price > 0.50:
                all_mentioned.add(price)
        except (ValueError, TypeError):
            pass

    suspicious = []
    for price in all_mentioned:
        if price not in known_prices:
            is_sum_of_known = _is_valid_derived_price(price, known_prices)
            if not is_sum_of_known:
                suspicious.append(price)

    return {
        "valid": len(suspicious) == 0,
        "suspicious_prices": suspicious,
        "checked_count": len(all_mentioned),
        "known_prices_loaded": len(known_prices),
    }


def _is_valid_derived_price(price: float, known: set[float]) -> bool:
    """Check if a price could be a valid sum/product of known prices.

    Allows computed totals (quantity * unit_price) and subtotals.
    """
    for kp in known:
        if kp == 0:
            continue
        ratio = price / kp
        if ratio == int(ratio) and 1 <= ratio <= 1000:
            return True
        if abs(ratio - round(ratio)) < 0.005 and 1 <= round(ratio) <= 1000:
            return True
    return False
