"""OpenAI Responses API service for the BMC Uruguay panel quotation assistant.

Uses the Responses API (NOT the deprecated Assistants API v2, shutdown Aug 2026):
- AsyncOpenAI client for non-blocking I/O (Fix C1)
- gpt-4.1-nano for cost optimization ($0.10/1M input tokens)
- previous_response_id for prompt caching (75% discount on cached tokens)
- file_search tool for RAG against the BMC product knowledge base vector store
- max_num_results=3 to limit RAG context injection (~2400 tokens max)
- Stale response_id recovery via BadRequestError catch (Fix H4)

Token budget per request (estimated):
- System prompt: ~150 tokens
- User message: ~50 tokens
- RAG context (3 chunks × ~800 tokens): ~2400 tokens
- Total input: ~2600 tokens
- Output: ~200 tokens
- Cost per message: ~$0.00034 (uncached) or ~$0.00015 (cached)
"""

import logging
from dataclasses import dataclass

import openai
from openai import AsyncOpenAI

from .config import ESCALATION_KEYWORDS
from .retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

PDF_TRIGGER_TOKEN = "[SEND_PDF]"


@dataclass
class ResponseResult:
    """Result of an OpenAI Responses API call."""

    text: str
    response_id: str
    should_send_pdf: bool


class OpenAIService:
    """Manages interactions with OpenAI Responses API.

    Uses AsyncOpenAI to avoid blocking the FastAPI/uvicorn event loop
    during model inference (2-8 seconds per request).
    """

    def __init__(
        self,
        api_key: str,
        vector_store_id: str,
        model: str = "gpt-4.1-nano",
        max_search_results: int = 3,
        system_prompt: str = "",
    ):
        self._client = AsyncOpenAI(api_key=api_key)
        self._vector_store_id = vector_store_id
        self._model = model
        self._max_search_results = max_search_results
        self._system_prompt = system_prompt

    async def send_message(
        self,
        user_text: str,
        previous_response_id: str | None = None,
    ) -> ResponseResult:
        """Send a message and get AI response with RAG context.

        Uses previous_response_id for conversation chaining, which:
        1. Preserves conversation history server-side (no manual management)
        2. Enables 75% prompt caching discount on gpt-4.1-nano
        3. Compresses context automatically via compaction

        Includes stale response_id recovery (Fix H4): if previous_response_id
        is expired/invalid, automatically retries without chaining to start
        a fresh conversation instead of permanently failing.

        Args:
            user_text: The user's message text.
            previous_response_id: ID of the last response in this
                conversation, or None for the first message.

        Returns:
            ResponseResult with generated text, response ID, and
            PDF dispatch flag.
        """
        try:
            return await retry_with_backoff(
                self._do_request,
                user_text,
                previous_response_id,
                max_retries=3,
            )
        except openai.BadRequestError as exc:
            # Fix H4: Stale response_id — retry without chaining
            if previous_response_id and "previous_response" in str(exc).lower():
                logger.warning(
                    "Stale response_id %s — starting fresh conversation",
                    previous_response_id,
                )
                try:
                    return await retry_with_backoff(
                        self._do_request,
                        user_text,
                        None,  # Fresh conversation
                        max_retries=2,
                    )
                except Exception:
                    logger.exception("Fresh conversation also failed")
            else:
                logger.exception("OpenAI BadRequestError (not stale response_id)")
            return self._error_result(previous_response_id)
        except Exception:
            logger.exception("OpenAI Responses API call failed")
            return self._error_result(previous_response_id)

    async def _do_request(
        self,
        user_text: str,
        previous_response_id: str | None,
    ) -> ResponseResult:
        """Execute a single Responses API call."""
        kwargs: dict = {
            "model": self._model,
            "input": user_text,
            "tools": [
                {
                    "type": "file_search",
                    "vector_store_ids": [self._vector_store_id],
                    "max_num_results": self._max_search_results,
                }
            ],
            "instructions": self._system_prompt,
        }

        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id

        response = await self._client.responses.create(**kwargs)

        # Extract text from response (multiple fallback strategies)
        text = getattr(response, "output_text", None) or ""
        if not text:
            for item in getattr(response, "output", []):
                if getattr(item, "type", "") == "message":
                    for part in getattr(item, "content", []):
                        if getattr(part, "type", "") in ("output_text", "text"):
                            text = getattr(part, "text", "")
                            if text:
                                break
                    if text:
                        break

        # Detect PDF trigger token
        should_send_pdf = PDF_TRIGGER_TOKEN in text
        if should_send_pdf:
            text = text.replace(PDF_TRIGGER_TOKEN, "").strip()

        return ResponseResult(
            text=text or "Lo siento, no pude procesar tu consulta. ¿Podrías reformularla?",
            response_id=response.id,
            should_send_pdf=should_send_pdf,
        )

    @staticmethod
    def _error_result(previous_response_id: str | None) -> ResponseResult:
        """Return a graceful error message when OpenAI fails."""
        return ResponseResult(
            text=(
                "En este momento los sistemas experimentan un volumen inusual. "
                "¿Podría reiterar la consulta en unos minutos?"
            ),
            response_id=previous_response_id or "",
            should_send_pdf=False,
        )

    @staticmethod
    def detect_escalation_intent(user_text: str) -> bool:
        """Check if user wants to talk to a human agent.

        Uses keyword matching against ESCALATION_KEYWORDS. This is
        intentionally simple — semantic detection would require an
        additional API call, wasting ~$0.00034 in tokens per message.

        Args:
            user_text: The user's message text.

        Returns:
            True if escalation intent is detected.
        """
        text_lower = user_text.lower()
        return any(keyword in text_lower for keyword in ESCALATION_KEYWORDS)
