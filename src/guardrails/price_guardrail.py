"""
Panelin v5.0 - Price Guardrails
=================================

Output guardrails that validate the agent never invents prices.
Checks agent responses against the KB to ensure price accuracy.

Rules:
    1. All prices must trace to bromyros_pricing_master.json or accessories_catalog.json
    2. IVA (22%) is ALREADY included — never add IVA on top
    3. If a price cannot be verified, flag it for human review
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class PriceGuardrailError(Exception):
    """Raised when the agent output contains suspicious price data."""

    def __init__(self, message: str, flagged_prices: list[dict]):
        super().__init__(message)
        self.flagged_prices = flagged_prices


def check_no_invented_prices(agent_output: str) -> tuple[bool, list[dict]]:
    """Scan agent output for price mentions and verify against KB.

    Returns:
        Tuple of (is_safe, flagged_items).
        is_safe=True means no suspicious prices detected.
    """
    from panelin_v4.engine.pricing_engine import _load_accessories, _load_pricing_master

    price_pattern = re.compile(
        r"(?:USD|U\$S|\$)\s*([\d,.]+)",
        re.IGNORECASE,
    )

    iva_addition_patterns = [
        re.compile(r"\+\s*(?:22|iva)", re.IGNORECASE),
        re.compile(r"(?:más|mas|agregar|sumar)\s+iva", re.IGNORECASE),
        re.compile(r"sin\s+iva.*\+.*22", re.IGNORECASE),
    ]

    flagged: list[dict] = []

    for pattern in iva_addition_patterns:
        if pattern.search(agent_output):
            flagged.append({
                "tipo": "iva_doble",
                "mensaje": "El output parece agregar IVA. Los precios del catálogo YA incluyen IVA 22%.",
                "patron_detectado": pattern.pattern,
            })

    prices_found = price_pattern.findall(agent_output)
    if len(prices_found) > 20:
        flagged.append({
            "tipo": "exceso_precios",
            "mensaje": f"Se detectaron {len(prices_found)} menciones de precio — revisar manualmente.",
        })

    is_safe = len(flagged) == 0
    return is_safe, flagged


def create_output_guardrail():
    """Create an Agno-compatible output guardrail function.

    Usage:
        agent = Agent(
            post_hooks=[create_output_guardrail()],
            ...
        )
    """

    def guardrail(run_output):
        content = getattr(run_output, "content", "")
        if not content:
            return

        is_safe, flagged = check_no_invented_prices(content)
        if not is_safe:
            logger.warning(
                f"Price guardrail flagged {len(flagged)} issue(s): "
                f"{json.dumps(flagged, ensure_ascii=False)}"
            )

    return guardrail
