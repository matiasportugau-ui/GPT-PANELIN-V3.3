"""Tests for OpenAI Responses API service.

Fix cross-#1: Patches AsyncOpenAI (not OpenAI) and uses AsyncMock
for responses.create since it's now an async call.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from whatsapp_bot.openai_service import OpenAIService, ResponseResult


class MockResponse:
    """Simulates an OpenAI Responses API response object."""

    def __init__(self, text: str, response_id: str = "resp_test123"):
        self.output_text = text
        self.id = response_id
        self.output = []


class TestOpenAIService:
    @pytest.fixture
    def service(self):
        """Create service with mocked AsyncOpenAI client (Fix cross-#1)."""
        with patch("whatsapp_bot.openai_service.AsyncOpenAI") as mock_cls:
            svc = OpenAIService(
                api_key="test-key",
                vector_store_id="vs_test",
                system_prompt="Test prompt",
            )
            yield svc

    @pytest.mark.asyncio
    async def test_send_first_message(self, service):
        """First message: no previous_response_id."""
        service._client.responses.create = AsyncMock(
            return_value=MockResponse("El ISODEC EPS 100mm cuesta USD 46.07/m² + IVA.")
        )

        result = await service.send_message("Necesito paneles para techo")

        assert result.text == "El ISODEC EPS 100mm cuesta USD 46.07/m² + IVA."
        assert result.response_id == "resp_test123"
        assert result.should_send_pdf is False
        # Verify no previous_response_id was passed
        call_kwargs = service._client.responses.create.call_args[1]
        assert "previous_response_id" not in call_kwargs

    @pytest.mark.asyncio
    async def test_send_continuation(self, service):
        """Continuation: includes previous_response_id for caching."""
        service._client.responses.create = AsyncMock(
            return_value=MockResponse("El ISODEC EPS 100mm tiene autoportancia de 5.5m.")
        )

        await service.send_message("Cual es la autoportancia?", "resp_previous")

        call_kwargs = service._client.responses.create.call_args[1]
        assert call_kwargs["previous_response_id"] == "resp_previous"

    @pytest.mark.asyncio
    async def test_pdf_trigger_detected(self, service):
        """Response containing [SEND_PDF] token should set flag."""
        service._client.responses.create = AsyncMock(
            return_value=MockResponse("[SEND_PDF] Aqui tiene su cotizacion.")
        )

        result = await service.send_message("Envieme la cotizacion en PDF")

        assert result.should_send_pdf is True
        assert "[SEND_PDF]" not in result.text
        assert "cotizacion" in result.text

    @pytest.mark.asyncio
    async def test_api_error_graceful_degradation(self, service):
        """API failure should return friendly error, not crash."""
        service._client.responses.create = AsyncMock(
            side_effect=Exception("API down")
        )

        result = await service.send_message("Hola")

        assert "volumen inusual" in result.text
        assert result.should_send_pdf is False
        assert result.response_id == ""

    @pytest.mark.asyncio
    async def test_empty_response_fallback(self, service):
        """Empty response text should use fallback message."""
        service._client.responses.create = AsyncMock(
            return_value=MockResponse("")
        )

        result = await service.send_message("Hola")

        assert "reformularla" in result.text


class TestEscalationDetection:
    """Tests for detect_escalation_intent keyword matching."""

    def test_escalation_keywords(self):
        assert OpenAIService.detect_escalation_intent("Quiero hablar con humano")
        assert OpenAIService.detect_escalation_intent("Necesito un asesor")
        assert OpenAIService.detect_escalation_intent("Tengo una queja")
        assert OpenAIService.detect_escalation_intent("quiero reclamar algo")
        assert OpenAIService.detect_escalation_intent("PERSONA REAL por favor")

    def test_no_false_escalation(self):
        assert not OpenAIService.detect_escalation_intent("Busco una casa")
        assert not OpenAIService.detect_escalation_intent("¿Cuánto cuesta?")
        assert not OpenAIService.detect_escalation_intent("Hola buenos días")
        assert not OpenAIService.detect_escalation_intent("Quiero ver propiedades")
