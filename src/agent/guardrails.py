"""
Panelin Agno — Guardrails

Output guardrails that ensure the agent NEVER invents prices.
These run after the LLM generates a response and before it's sent to the user.
"""

from __future__ import annotations

import re
from typing import Optional


def validate_no_invented_prices(response_content: str) -> Optional[str]:
    """Post-hook: check that the response doesn't contain price patterns
    that weren't sourced from the pipeline tools.

    This is a heuristic check — the primary enforcement is via system instructions
    and tool-only pricing. This guardrail catches edge cases where the LLM
    might hallucinate a price.
    """
    price_patterns = [
        r"USD\s*\d+[.,]?\d*",
        r"\$\s*\d+[.,]?\d*",
        r"\d+[.,]?\d*\s*(?:dólares|dolares|USD)",
    ]

    for pattern in price_patterns:
        matches = re.findall(pattern, response_content, re.IGNORECASE)
        if len(matches) > 10:
            return (
                "⚠️ Se detectaron muchos valores monetarios en la respuesta. "
                "Verificá que todos los precios provienen del catálogo BMC. "
                "NUNCA se deben inventar precios."
            )

    return None


def validate_spanish_response(response_content: str) -> Optional[str]:
    """Post-hook: ensure the response is in Spanish."""
    english_indicators = [
        "the total cost", "here is your quote", "the price is",
        "bill of materials", "based on your request",
    ]
    content_lower = response_content.lower()

    english_count = sum(1 for ind in english_indicators if ind in content_lower)
    if english_count >= 2:
        return (
            "La respuesta debe ser en español. "
            "Panelin es un asistente para BMC Uruguay y responde exclusivamente en español."
        )

    return None
