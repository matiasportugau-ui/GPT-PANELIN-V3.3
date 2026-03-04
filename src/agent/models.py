"""Model factory helpers for Agno agents and workflows."""

from __future__ import annotations

from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

from src.core.config import AppSettings


def build_chat_model(settings: AppSettings):
    """Build the configured chat model instance."""
    if settings.panelin_model_provider == "anthropic":
        return Claude(
            id=settings.anthropic_model_id,
            api_key=settings.anthropic_api_key,
            temperature=0.1,
            max_tokens=1200,
        )
    return OpenAIChat(
        id=settings.openai_model_id,
        api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=1200,
    )
