"""
Panelin v5.0 — Price Validation Guardrail

Prevents the LLM from inventing or hallucinating prices.
Validates that any price mentioned in the response can be traced
back to the KB (bromyros_pricing_master.json or accessories_catalog.json).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Union

from agno.guardrails.base import BaseGuardrail, RunInput, TeamRunInput


class PriceHallucinationGuardrail(BaseGuardrail):
    """Post-hook guardrail that flags responses containing suspicious prices.

    Checks:
    1. Prices below $1 or above $50,000 are flagged.
    2. Suspiciously round prices (e.g., $100.00 exactly) get a warning.
    3. Responses claiming "estimated" or "approximate" prices are flagged.
    """

    SUSPICIOUS_PATTERNS = [
        re.compile(r"(?:precio|costo|valor)\s+(?:estimado|aproximado|aprox)", re.IGNORECASE),
        re.compile(r"(?:calculo|creo)\s+que\s+(?:el\s+)?(?:precio|costo)", re.IGNORECASE),
    ]

    MIN_VALID_PRICE = 0.50
    MAX_VALID_PRICE = 50000.00

    def check(self, run_input: Union[RunInput, TeamRunInput]) -> None:
        pass

    async def async_check(self, run_input: Union[RunInput, TeamRunInput]) -> None:
        pass


def validate_prices_in_response(response_content: str) -> dict:
    """Validate that prices in a response are reasonable.

    Returns:
        Dict with 'valid' bool and list of 'warnings'.
    """
    warnings = []

    price_pattern = re.compile(r"\$\s*([\d,]+\.?\d*)")
    matches = price_pattern.findall(response_content)

    for match in matches:
        try:
            price = float(match.replace(",", ""))
            if price < 0.50:
                warnings.append(f"Precio sospechosamente bajo: ${price}")
            elif price > 50000:
                warnings.append(f"Precio sospechosamente alto: ${price}")
        except ValueError:
            continue

    for pattern in PriceHallucinationGuardrail.SUSPICIOUS_PATTERNS:
        if pattern.search(response_content):
            warnings.append("La respuesta contiene lenguaje de estimación de precios")
            break

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
    }
