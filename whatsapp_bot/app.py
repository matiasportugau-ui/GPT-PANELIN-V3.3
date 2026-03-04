"""FastAPI application for the BMC Uruguay WhatsApp Bot (Panelin).

Endpoints:
    GET  /webhook         — Meta verification challenge (handshake)
    POST /webhook         — Incoming WhatsApp messages (webhook)
    POST /sync            — Trigger vector store sync (Cloud Scheduler)
    POST /admin/escalate  — Manual human escalation override (Amendment C)
    GET  /health          — Cloud Run health check

Architecture:
    1. POST /webhook returns 200 immediately (Meta 5-10s requirement)
    2. Message processing runs as a BackgroundTask within request lifecycle
    3. Cloud Run request-based billing keeps instance alive for BackgroundTasks
    4. All external API calls use AsyncOpenAI / httpx (non-blocking)

Incorporates fixes:
    - M7: Iterates all messages in batch webhooks
    - M9: Uses lifespan context manager (not deprecated @app.on_event)
    - Edge #2: Null check on hub_challenge
    - Amendment C: POST /admin/escalate endpoint
"""

import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from .config import Settings, load_settings
from .firestore_manager import SessionManager
from .openai_service import OpenAIService
from .vector_store_sync import run_nightly_sync
from .whatsapp_client import WhatsAppClient

# NOTE: panelin_sync provides Wolf API integration (customer persistence,
# conversation logging) — imported where needed for CRM operations.

logger = logging.getLogger(__name__)

# ── Module-level state (initialized in lifespan) ─────────────

settings: Settings | None = None
wa_client: WhatsAppClient | None = None
session_manager: SessionManager | None = None
openai_service: OpenAIService | None = None


# ── Application Lifespan (Fix M9) ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup, clean up on shutdown.

    Uses the modern lifespan pattern instead of deprecated
    @app.on_event('startup'/'shutdown') decorators.
    """
    global settings, wa_client, session_manager, openai_service

    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    wa_client = WhatsAppClient(
        token=settings.whatsapp_token,
        phone_number_id=settings.phone_number_id,
        api_version=settings.graph_api_version,
    )

    session_manager = SessionManager(timeout_hours=settings.timeout_hours)

    openai_service = OpenAIService(
        api_key=settings.openai_api_key,
        vector_store_id=settings.vector_store_id,
        model=settings.model,
        max_search_results=settings.max_search_results,
        system_prompt=settings.system_prompt,
    )

    logger.info(
        "WhatsApp Bot started (model=%s, vector_store=%s)",
        settings.model,
        settings.vector_store_id,
    )

    yield  # Application runs here

    # Shutdown
    if wa_client:
        await wa_client.close()
    logger.info("WhatsApp Bot shutdown complete")


app = FastAPI(
    title="BMC Uruguay WhatsApp Bot",
    description="Panelin - Technical sales assistant for construction panels powered by OpenAI + WhatsApp",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


# ── Webhook Endpoints ─────────────────────────────────────────

@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    """Meta webhook verification challenge.

    Meta sends a GET request with hub.mode, hub.verify_token,
    and hub.challenge. If the token matches, return the challenge
    as plain text to confirm domain ownership.
    """
    # Fix Edge #2: Null check on hub_challenge
    if (
        hub_mode == "subscribe"
        and hub_token == settings.verify_token
        and hub_challenge
    ):
        logger.info("Webhook verification successful")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("Webhook verification failed (mode=%s)", hub_mode)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
) -> dict:
    """Receive incoming WhatsApp messages.

    Security: Validates HMAC-SHA256 signature from Meta.
    Performance: Returns 200 immediately; processes in background.

    MUST always return 200 to Meta, even on internal errors,
    to prevent webhook retry storms (Meta retries for up to 7 days).
    """
    body = await request.body()

    # Verify HMAC signature
    if settings.meta_app_secret:
        if not WhatsAppClient.verify_signature(
            body, x_hub_signature_256 or "", settings.meta_app_secret
        ):
            logger.warning("Invalid webhook signature — rejecting request")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        return {"status": "invalid_json"}

    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored"}

    # Extract and process messages (Fix M7: iterate ALL messages in batch)
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "no_messages"}

        messages_queued = 0
        for message in value["messages"]:
            sender_id = message.get("from")
            msg_type = message.get("type")

            if msg_type == "text" and sender_id:
                text_body = message.get("text", {}).get("body", "")
                if text_body:
                    background_tasks.add_task(
                        process_incoming_message, sender_id, text_body
                    )
                    messages_queued += 1

        return {"status": "processing", "messages_queued": messages_queued}

    except (KeyError, IndexError, TypeError):
        return {"status": "parse_error"}


# ── Message Processing (Background Task) ──────────────────────

HANDOFF_MESSAGE = (
    "Comprendo. He transferido esta conversación al equipo técnico "
    "comercial de BMC Uruguay, quien se pondrá en contacto a la brevedad. "
    "Gracias por su paciencia."
)

REACTIVATION_MESSAGE = (
    "La sesión asistida ha concluido. El asistente Panelin de BMC Uruguay "
    "retoma el canal para futuras consultas. ¿En qué puedo ayudarle?"
)


async def process_incoming_message(wa_id: str, text_body: str) -> None:
    """Core message processing orchestrator.

    State machine:
    1. Get/create session (transactional, concurrency-safe)
    2. If AI inactive and not timed out → silent return
    3. If timed out → reactivate AI, notify user
    4. If escalation intent detected → deactivate AI, notify user
    5. Otherwise → send to OpenAI, deliver response via WhatsApp
    """
    try:
        # Step 1: Get session (sync Firestore call via threadpool)
        session = await run_in_threadpool(
            session_manager.get_or_create_session, wa_id
        )

        # Step 2: Human escalation — silent mode
        if not session.ai_active and not session.timed_out:
            logger.debug("AI inactive for %s — silent return", wa_id)
            return

        # Step 3: Timeout → reactivate
        if session.timed_out:
            logger.info("Escalation timed out for %s — reactivating AI", wa_id)
            await wa_client.send_text(wa_id, REACTIVATION_MESSAGE)

        # Step 4: Check escalation intent
        if OpenAIService.detect_escalation_intent(text_body):
            logger.info("Escalation intent detected for %s", wa_id)
            await run_in_threadpool(session_manager.set_ai_inactive, wa_id)
            await wa_client.send_text(wa_id, HANDOFF_MESSAGE)
            return

        # Step 5: Send to OpenAI and get response
        result = await openai_service.send_message(
            text_body, session.last_response_id
        )

        # Step 6: Update session with new response ID
        await run_in_threadpool(
            session_manager.update_response_id, wa_id, result.response_id
        )

        # Step 7: Deliver response
        if result.should_send_pdf:
            if result.text:
                await wa_client.send_text(wa_id, result.text)
            await wa_client.send_document(
                wa_id,
                "/app/panelin_reports/output/cotizacion.pdf",
                "Cotizacion_BMC_Uruguay.pdf",
                "Cotización técnica BMC Uruguay adjunta.",
            )
        else:
            await wa_client.send_text(wa_id, result.text)

    except Exception:
        logger.exception("Error processing message from %s", wa_id)
        try:
            await wa_client.send_text(
                wa_id,
                "Disculpe, ha ocurrido un error temporal. "
                "Por favor, intente nuevamente.",
            )
        except Exception:
            logger.exception("Failed to send error message to %s", wa_id)


# ── Sync Endpoint ─────────────────────────────────────────────

@app.post("/sync")
async def trigger_sync(
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> dict:
    """Trigger vector store synchronization.

    Protected by API key. Called by Cloud Scheduler (nightly)
    or manually for immediate sync.
    """
    if settings.sync_api_key and not hmac.compare_digest(
        x_api_key or "", settings.sync_api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not settings.kb_pricing_path:
        raise HTTPException(
            status_code=503, detail="KB pricing path not configured"
        )

    stats = await run_nightly_sync(
        openai_api_key=settings.openai_api_key,
        vector_store_id=settings.vector_store_id,
        pricing_path=settings.kb_pricing_path,
        kb_path=settings.kb_base_path,
        db=session_manager.db if session_manager else None,
    )

    return {
        "status": "completed",
        "stats": {
            "added": stats.added,
            "removed": stats.removed,
            "unchanged": stats.unchanged,
            "errors": stats.errors,
            "total_properties": stats.total_properties,
        },
    }


# ── Admin Endpoint (Amendment C) ──────────────────────────────

@app.post("/admin/escalate")
async def admin_escalate(
    wa_id: str = Query(..., description="WhatsApp phone number to escalate"),
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> dict:
    """Admin endpoint to manually pause AI for a specific user.

    Used by human agents to take over a conversation from the
    WhatsApp Business inbox or CRM dashboard.
    """
    if settings.sync_api_key and not hmac.compare_digest(
        x_api_key or "", settings.sync_api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid API key")

    await run_in_threadpool(session_manager.set_ai_inactive, wa_id)
    logger.info("Admin escalation: AI paused for %s", wa_id)
    return {"status": "escalated", "wa_id": wa_id}


# ── Health Check ──────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    """Health check endpoint for Cloud Run readiness probes."""
    return {"status": "healthy", "service": "whatsapp-bot"}
