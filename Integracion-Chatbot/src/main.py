"""
Webhook principal FastAPI para el Agente Inmobiliario Cognitivo.

Procesa webhooks entrantes de WhatsApp Cloud API (Meta) con:
- Verificación criptográfica HMAC SHA-256
- Procesamiento asíncrono en background tasks
- Delegación al pipeline de IA (OpenAI + Firestore + MCP)
"""

import hmac
import hashlib

import firebase_admin
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks

from src.config import META_APP_SECRET, VERIFY_TOKEN
from src.firestore_client import check_and_update_session
from src.openai_router import generate_response
from src.api_meta import send_whatsapp_message


# Inicialización de Firebase (singleton, usa GOOGLE_APPLICATION_CREDENTIALS)
firebase_admin.initialize_app()

app = FastAPI(title="PANELIN AI Webhook — Agente Inmobiliario Cognitivo")


# ==============================================================================
# Seguridad: Verificación HMAC SHA-256
# ==============================================================================

async def verify_signature(request: Request) -> None:
    """Verifica la firma criptográfica HMAC SHA-256 del payload de Meta.

    Raises:
        HTTPException: Si la firma es inválida o ausente.
    """
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.body()
    expected_hmac = hmac.new(
        META_APP_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    if not signature or not hmac.compare_digest(signature, f"sha256={expected_hmac}"):
        raise HTTPException(status_code=401, detail="Firma inválida")


# ==============================================================================
# Pipeline de Procesamiento
# ==============================================================================

async def process_pipeline(wa_id: str, text: str) -> None:
    """Pipeline completo: Firestore → OpenAI → WhatsApp.

    1. Verifica estado de sesión en Firestore (ai_active, thread_id).
    2. Si ai_active=False (operador humano activo), no procesa.
    3. Genera respuesta con OpenAI Responses API.
    4. Envía respuesta por WhatsApp.

    Args:
        wa_id: Número de WhatsApp del remitente.
        text: Contenido del mensaje de texto.
    """
    is_ai_active, thread_id = check_and_update_session(wa_id)

    if not is_ai_active:
        return  # Operador humano activo — silencio de la IA

    ai_response = await generate_response(text, thread_id)

    if ai_response:
        await send_whatsapp_message(wa_id, ai_response)


# ==============================================================================
# Endpoints del Webhook
# ==============================================================================

@app.get("/webhook")
async def verify_webhook(request: Request) -> int:
    """Verificación inicial del webhook (suscripción Meta).

    Meta envía un GET con hub.mode, hub.verify_token y hub.challenge.
    Si el token coincide, se responde con el challenge como entero.
    """
    if (
        request.query_params.get("hub.mode") == "subscribe"
        and request.query_params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return int(request.query_params.get("hub.challenge"))

    raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/webhook")
async def handle_webhook(request: Request, bg_tasks: BackgroundTasks) -> dict:
    """Receptor asíncrono principal de eventos de WhatsApp.

    Procesa el payload del webhook iterando correctamente sobre las listas
    anidadas de entry → changes → messages. Cada mensaje de texto se delega
    a una tarea en segundo plano para responder rápido a Meta (HTTP 200).

    NOTA: En producción, descomentar la línea de verify_signature.
    """
    # En producción, descomentar la siguiente línea:
    # await verify_signature(request)

    body = await request.json()

    if body.get("object") == "whatsapp_business_account":
        # Iterar correctamente sobre las listas anidadas del payload
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                for msg in change.get("value", {}).get("messages", []):
                    if msg.get("type") == "text":
                        bg_tasks.add_task(
                            process_pipeline,
                            msg["from"],
                            msg["text"]["body"],
                        )
        return {"status": "ok"}

    raise HTTPException(status_code=404, detail="Not Supported")
