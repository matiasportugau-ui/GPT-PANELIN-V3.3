"""WhatsApp Cloud API client for text messages and document delivery.

Architecture:
- Uses httpx.AsyncClient with connection pooling for low-latency calls
- Two-phase document upload: (1) upload binary to Meta cache, (2) send message referencing media_id
- HMAC-SHA256 signature verification for webhook security

Cost note: Service messages within 24h window are FREE. Template messages
outside window cost $0.004-0.14/msg depending on category and region.

CRITICAL: Do NOT set Content-Type header manually on media upload requests.
Let httpx auto-generate the multipart boundary. Manual Content-Type causes
OAuthException Code 100 from Meta's Graph API.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from .retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

MAX_DOCUMENT_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB Meta limit


class WhatsAppClient:
    """Async client for WhatsApp Cloud API messaging."""

    def __init__(
        self,
        token: str,
        phone_number_id: str,
        api_version: str = "v21.0",
    ):
        self.base_url = (
            f"https://graph.facebook.com/{api_version}/{phone_number_id}"
        )
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()

    # ── Text Messages ────────────────────────────────────────

    async def send_text(self, to: str, text: str) -> int:
        """Send a free-form text message within the 24h service window.

        Args:
            to: Recipient phone number (wa_id format, e.g. '34612345678').
            text: Message body (truncated to 4096 chars per Meta limit).

        Returns:
            HTTP status code from Meta API.
        """
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text[:4096]},
        }

        async def _do_send() -> int:
            resp = await self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.status_code

        return await retry_with_backoff(_do_send, max_retries=3)

    # ── Template Messages (24h window expired) ───────────────

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "es",
    ) -> int:
        """Send a pre-approved template message (required outside 24h window).

        Meta requires template messages when contacting users outside the
        24-hour service window opened by their last inbound message.

        Args:
            to: Recipient phone number.
            template_name: Name of the pre-approved template in Meta Business Manager.
            language_code: ISO 639-1 language code (default: 'es' for Spanish).

        Returns:
            HTTP status code from Meta API.
        """
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        async def _do_send() -> int:
            resp = await self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.status_code

        return await retry_with_backoff(_do_send, max_retries=3)

    async def send_text_or_template(
        self,
        to: str,
        text: str,
        last_interaction: datetime | None = None,
        template_name: str = "reactivation_message",
    ) -> int:
        """Send free-form text within 24h window, or template outside it.

        Automatically switches to template messages when the 24h service
        window has expired, preventing message rejection by Meta.

        Args:
            to: Recipient phone number.
            text: Message body (used only within 24h window).
            last_interaction: Timestamp of user's last inbound message.
            template_name: Fallback template name for outside 24h window.

        Returns:
            HTTP status code from Meta API.
        """
        if last_interaction:
            elapsed = datetime.now(timezone.utc) - last_interaction
            if elapsed > timedelta(hours=24):
                logger.info(
                    "24h window expired for %s (elapsed=%s) — using template",
                    to,
                    elapsed,
                )
                return await self.send_template(to, template_name)
        return await self.send_text(to, text)

    # ── Document Messages (Two-Phase) ────────────────────────

    async def send_document(
        self,
        to: str,
        filepath: str,
        filename: str,
        caption: str,
    ) -> int | None:
        """Upload and send a PDF document via WhatsApp.

        Phase 1: Upload binary to Meta's media cache → get media_id.
        Phase 2: Send document message referencing media_id.

        Args:
            to: Recipient phone number.
            filepath: Local path to the PDF file.
            filename: Display name shown in client (e.g. 'Dossier.pdf').
            caption: Descriptive text shown alongside the document.

        Returns:
            HTTP status code on success, None on failure.
        """
        path = Path(filepath)
        if not path.exists():
            logger.error("Document not found: %s", filepath)
            return None

        file_size = path.stat().st_size
        if file_size > MAX_DOCUMENT_SIZE_BYTES:
            logger.error(
                "Document too large: %d bytes (max %d)",
                file_size,
                MAX_DOCUMENT_SIZE_BYTES,
            )
            return None

        # Phase 1: Upload to Meta media cache
        media_id = await self._upload_media(filepath, filename)
        if not media_id:
            return None

        # Phase 2: Send document message
        return await self._send_media_message(to, media_id, filename, caption)

    async def _upload_media(self, filepath: str, filename: str) -> str | None:
        """Upload file to Meta's media storage. Returns media_id.

        CRITICAL: Do NOT set Content-Type header manually.
        httpx auto-generates the multipart boundary. Setting it
        manually causes OAuthException Code 100.
        """
        upload_url = f"{self.base_url}/media"

        async def _do_upload() -> str | None:
            with open(filepath, "rb") as f:
                resp = await self._client.post(
                    upload_url,
                    data={
                        "messaging_product": "whatsapp",
                        "type": "application/pdf",
                    },
                    files={"file": (filename, f, "application/pdf")},
                )
            resp.raise_for_status()
            return resp.json().get("id")

        try:
            return await retry_with_backoff(_do_upload, max_retries=2)
        except Exception:
            logger.exception("Media upload failed for %s", filepath)
            return None

    async def _send_media_message(
        self,
        to: str,
        media_id: str,
        filename: str,
        caption: str,
    ) -> int:
        """Send a document message referencing an uploaded media_id."""
        url = f"{self.base_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": filename,
                "caption": caption,
            },
        }

        async def _do_send() -> int:
            resp = await self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.status_code

        return await retry_with_backoff(_do_send, max_retries=3)

    # ── Webhook Security ─────────────────────────────────────

    @staticmethod
    def verify_signature(
        payload: bytes,
        signature_header: str,
        app_secret: str,
    ) -> bool:
        """Verify Meta webhook HMAC-SHA256 signature.

        Uses constant-time comparison (hmac.compare_digest) to prevent
        timing attacks. The signature header format is 'sha256=<hex_digest>'.

        Args:
            payload: Raw request body bytes (NOT parsed JSON).
            signature_header: Value of X-Hub-Signature-256 header.
            app_secret: Meta App Secret (NOT the verify token).

        Returns:
            True if the signature is valid and authentic.
        """
        if not signature_header or not app_secret:
            return False

        expected = hmac.new(
            app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            signature_header,
            f"sha256={expected}",
        )
