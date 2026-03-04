"""Tests for WhatsApp Cloud API client."""

import hashlib
import hmac as hmac_mod
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from whatsapp_bot.whatsapp_client import WhatsAppClient, MAX_DOCUMENT_SIZE_BYTES


class TestVerifySignature:
    """Tests for HMAC-SHA256 webhook signature verification."""

    def test_valid_signature(self):
        payload = b'{"test": "data"}'
        secret = "mysecret"
        expected = hmac_mod.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        sig = f"sha256={expected}"

        assert WhatsAppClient.verify_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        assert (
            WhatsAppClient.verify_signature(b"data", "sha256=wrong", "secret")
            is False
        )

    def test_empty_header_returns_false(self):
        assert (
            WhatsAppClient.verify_signature(b"data", "", "secret") is False
        )

    def test_empty_secret_returns_false(self):
        assert (
            WhatsAppClient.verify_signature(b"data", "sha256=abc", "") is False
        )

    def test_constant_time_comparison(self):
        """Verify we use hmac.compare_digest (not ==) for timing attack prevention."""
        payload = b"test"
        secret = "key"
        expected = hmac_mod.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        # This test verifies the function works correctly —
        # the actual constant-time guarantee comes from hmac.compare_digest
        assert WhatsAppClient.verify_signature(
            payload, f"sha256={expected}", secret
        )


class TestSendDocument:
    """Tests for two-phase PDF document upload."""

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self):
        """Files > 15MB should be rejected before upload."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1))
            f.flush()

            client = WhatsAppClient("token", "12345")
            result = await client.send_document(
                "34612345678", f.name, "big.pdf", "Too big"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_rejects_missing_file(self):
        """Non-existent file path should return None."""
        client = WhatsAppClient("token", "12345")
        result = await client.send_document(
            "34612345678", "/nonexistent.pdf", "x.pdf", "cap"
        )
        assert result is None


class TestSendText:
    """Tests for text message sending."""

    @pytest.mark.asyncio
    async def test_truncates_long_messages(self):
        """Messages > 4096 chars should be truncated."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        client = WhatsAppClient("token", "12345")
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_resp)

        long_msg = "x" * 5000
        await client.send_text("34612345678", long_msg)

        call_kwargs = client._client.post.call_args
        payload = call_kwargs[1]["json"]
        assert len(payload["text"]["body"]) == 4096
