"""Tests for FastAPI webhook endpoints and health check."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client(mock_wa_client, mock_openai_service, mock_session_manager):
    """Async test client with mocked dependencies."""
    with (
        patch("whatsapp_bot.app.wa_client", mock_wa_client),
        patch("whatsapp_bot.app.openai_service", mock_openai_service),
        patch("whatsapp_bot.app.session_manager", mock_session_manager),
        patch("whatsapp_bot.app.settings") as mock_settings,
    ):
        mock_settings.verify_token = "test-verify-token"
        mock_settings.meta_app_secret = "test-app-secret"
        mock_settings.sync_api_key = "test-sync-key"
        mock_settings.inmoenter_feed_url = ""
        mock_settings.log_level = "WARNING"

        from whatsapp_bot.app import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


def _sign(payload: bytes, secret: str = "test-app-secret") -> str:
    """Compute HMAC-SHA256 signature matching Meta's format."""
    h = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={h}"


@pytest.mark.asyncio
class TestWebhookVerification:
    """Tests for GET /webhook (Meta verification challenge)."""

    async def test_valid_token_returns_challenge(self, client):
        resp = await client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "challenge_string_123",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "challenge_string_123"

    async def test_invalid_token_returns_403(self, client):
        resp = await client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "WRONG-TOKEN",
                "hub.challenge": "challenge_string_123",
            },
        )
        assert resp.status_code == 403

    async def test_missing_challenge_returns_403(self, client):
        """Fix Edge #2: Missing hub.challenge should not crash."""
        resp = await client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
            },
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestWebhookPost:
    """Tests for POST /webhook (incoming messages)."""

    async def test_valid_text_message(self, client, sample_webhook_payload):
        body = json.dumps(sample_webhook_payload).encode()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": _sign(body),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processing"
        assert data["messages_queued"] == 1

    async def test_invalid_signature_returns_401(self, client, sample_webhook_payload):
        body = json.dumps(sample_webhook_payload).encode()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid_signature",
            },
        )
        assert resp.status_code == 401

    async def test_status_update_ignored(self, client):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {"statuses": [{}]},
                            "field": "messages",
                        }
                    ]
                }
            ],
        }
        body = json.dumps(payload).encode()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": _sign(body),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_messages"

    async def test_non_whatsapp_object_ignored(self, client):
        payload = {"object": "something_else"}
        body = json.dumps(payload).encode()
        resp = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": _sign(body),
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
class TestHealth:
    """Tests for GET /health."""

    async def test_health_returns_200(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "whatsapp-bot"
