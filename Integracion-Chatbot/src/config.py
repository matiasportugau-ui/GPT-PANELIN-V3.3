"""
Configuración centralizada del Agente Inmobiliario Cognitivo.

Todas las variables de entorno se importan desde este módulo.
Usar: from src.config import WHATSAPP_TOKEN, OPENAI_API_KEY, ...
"""

import os

# --- Meta / WhatsApp Cloud API ---
VERIFY_TOKEN: str = os.environ.get("VERIFY_TOKEN", "")
META_APP_SECRET: str = os.environ.get("META_APP_SECRET", "")
WHATSAPP_TOKEN: str = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID: str = os.environ.get("PHONE_NUMBER_ID", "")
WHATSAPP_API_BASE: str = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}"

# --- OpenAI ---
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
VECTOR_STORE_ID: str = os.environ.get("VECTOR_STORE_ID", "")

# --- CRM Inmoenter (PANELIN-API) ---
INMOENTER_API_KEY: str = os.environ.get("INMOENTER_API_KEY", "")

# --- Parámetros del Sistema ---
TIMEOUT_HOURS: int = 24  # Horas antes de reactivar IA tras handoff humano
MCP_SERVER_URL: str = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")

# --- Keywords para Escalado Humano ---
HANDOFF_KEYWORDS: list[str] = ["humano", "agente", "asesor"]
