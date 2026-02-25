"""Centralized configuration for the WhatsApp Bot service.

All values are loaded from environment variables at startup.
The Settings dataclass is frozen (immutable) to prevent accidental mutation.
Uses _safe_int() for integer env vars to prevent startup crashes on invalid values.
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente inmobiliario profesional. Respondes consultas sobre propiedades "
    "disponibles usando exclusivamente la información del catálogo indexado.\n"
    "Reglas:\n"
    "1. Sé conciso: máximo 150 palabras por respuesta.\n"
    "2. Si no encuentras propiedades que coincidan, dilo claramente.\n"
    "3. Si el cliente pide documentación o un dossier, incluye el token [SEND_PDF] al inicio.\n"
    "4. Nunca inventes propiedades que no estén en el catálogo.\n"
    "5. Responde en el idioma del cliente.\n"
    "6. Incluye siempre: precio, ubicación y características principales.\n"
    "7. Si el cliente quiere hablar con un humano, respóndele que lo transferirás."
)

ESCALATION_KEYWORDS = [
    "hablar con humano",
    "hablar con una persona",
    "agente",
    "asesor",
    "queja",
    "persona real",
    "operador",
    "no me sirve",
    "quiero reclamar",
]


def _safe_int(env_var: str, default: int) -> int:
    """Parse integer from environment variable with fallback to default.

    Prevents container startup crashes when an env var contains
    an invalid non-integer value (e.g. 'abc').
    """
    raw = os.environ.get(env_var, str(default))
    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning(
            "Invalid integer for %s='%s', using default %d", env_var, raw, default
        )
        return default


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # --- Meta / WhatsApp Cloud API ---
    verify_token: str = ""
    meta_app_secret: str = ""
    whatsapp_token: str = ""
    phone_number_id: str = ""
    graph_api_version: str = "v21.0"

    # --- OpenAI ---
    openai_api_key: str = ""
    vector_store_id: str = ""
    model: str = "gpt-4.1-nano"
    max_search_results: int = 3
    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    # --- Firestore ---
    timeout_hours: int = 24

    # --- Inmoenter / PANELIN-API ---
    inmoenter_api_key: str = ""
    inmoenter_feed_url: str = ""

    # --- Internal ---
    sync_api_key: str = ""
    log_level: str = "INFO"


def load_settings() -> Settings:
    """Load settings from environment variables.

    Returns a frozen Settings instance. Missing optional values
    default to empty strings; the service will degrade gracefully
    if non-critical integrations are unconfigured.
    """
    return Settings(
        verify_token=os.environ.get("VERIFY_TOKEN", ""),
        meta_app_secret=os.environ.get("META_APP_SECRET", ""),
        whatsapp_token=os.environ.get("WHATSAPP_TOKEN", ""),
        phone_number_id=os.environ.get("PHONE_NUMBER_ID", ""),
        graph_api_version=os.environ.get("GRAPH_API_VERSION", "v21.0"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        vector_store_id=os.environ.get("VECTOR_STORE_ID", ""),
        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-nano"),
        max_search_results=_safe_int("MAX_SEARCH_RESULTS", 3),
        system_prompt=os.environ.get("SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        timeout_hours=_safe_int("TIMEOUT_HOURS", 24),
        inmoenter_api_key=os.environ.get("INMOENTER_API_KEY", ""),
        inmoenter_feed_url=os.environ.get("INMOENTER_FEED_URL", ""),
        sync_api_key=os.environ.get("SYNC_API_KEY", ""),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
