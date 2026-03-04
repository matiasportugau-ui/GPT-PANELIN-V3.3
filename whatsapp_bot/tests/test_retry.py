"""Tests for exponential backoff retry logic.

Fix H6: All httpx.Response() constructors include request= parameter
to prevent constructor errors in strict httpx versions.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from whatsapp_bot.retry_utils import _is_retryable, retry_with_backoff


def _make_http_error(status_code: int) -> httpx.HTTPStatusError:
    """Create an HTTPStatusError with proper request/response objects (Fix H6)."""
    request = httpx.Request("GET", "http://test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=response
    )


class TestIsRetryable:
    """Tests for the error classification function."""

    def test_timeout_is_retryable(self):
        assert _is_retryable(httpx.ReadTimeout("timeout")) is True

    def test_connect_timeout_is_retryable(self):
        assert _is_retryable(httpx.ConnectTimeout("connect")) is True

    def test_429_is_retryable(self):
        assert _is_retryable(_make_http_error(429)) is True

    def test_500_is_retryable(self):
        assert _is_retryable(_make_http_error(500)) is True

    def test_502_is_retryable(self):
        assert _is_retryable(_make_http_error(502)) is True

    def test_503_is_retryable(self):
        assert _is_retryable(_make_http_error(503)) is True

    def test_504_is_retryable(self):
        assert _is_retryable(_make_http_error(504)) is True

    def test_400_not_retryable(self):
        assert _is_retryable(_make_http_error(400)) is False

    def test_401_not_retryable(self):
        assert _is_retryable(_make_http_error(401)) is False

    def test_404_not_retryable(self):
        assert _is_retryable(_make_http_error(404)) is False

    def test_422_not_retryable(self):
        assert _is_retryable(_make_http_error(422)) is False

    def test_value_error_not_retryable(self):
        assert _is_retryable(ValueError("bad")) is False

    def test_runtime_error_not_retryable(self):
        assert _is_retryable(RuntimeError("unexpected")) is False


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff async function."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Function that succeeds should return immediately."""
        func = AsyncMock(return_value="ok")
        result = await retry_with_backoff(func)
        assert result == "ok"
        assert func.call_count == 1

    @pytest.mark.asyncio
    @patch("whatsapp_bot.retry_utils.asyncio.sleep", new_callable=AsyncMock)
    async def test_retries_then_succeeds(self, mock_sleep):
        """Should retry on 429 and eventually succeed."""
        err = _make_http_error(429)
        func = AsyncMock(side_effect=[err, err, "success"])

        result = await retry_with_backoff(
            func, max_retries=5, base_delay=0.01
        )

        assert result == "success"
        assert func.call_count == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    @patch("whatsapp_bot.retry_utils.asyncio.sleep", new_callable=AsyncMock)
    async def test_max_retries_exhausted(self, mock_sleep):
        """Should raise after exhausting all retries."""
        err = _make_http_error(500)
        func = AsyncMock(side_effect=err)

        with pytest.raises(httpx.HTTPStatusError):
            await retry_with_backoff(func, max_retries=2, base_delay=0.01)

        # initial call + 2 retries = 3 total
        assert func.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self):
        """400 errors should raise immediately without retrying."""
        err = _make_http_error(400)
        func = AsyncMock(side_effect=err)

        with pytest.raises(httpx.HTTPStatusError):
            await retry_with_backoff(func, max_retries=5)

        assert func.call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_non_http_error_not_retried(self):
        """Non-HTTP errors should propagate immediately."""
        func = AsyncMock(side_effect=ValueError("bad input"))

        with pytest.raises(ValueError, match="bad input"):
            await retry_with_backoff(func, max_retries=5)

        assert func.call_count == 1

    @pytest.mark.asyncio
    @patch("whatsapp_bot.retry_utils.asyncio.sleep", new_callable=AsyncMock)
    async def test_delays_increase_exponentially(self, mock_sleep):
        """Delays should follow exponential backoff pattern."""
        err = _make_http_error(503)
        func = AsyncMock(side_effect=[err, err, err, "ok"])

        await retry_with_backoff(func, max_retries=5, base_delay=1.0)

        assert mock_sleep.call_count == 3
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        # Delays should be roughly: 1-2s, 2-3s, 4-5s (with jitter)
        assert delays[0] >= 1.0
        assert delays[1] >= 2.0
        assert delays[2] >= 4.0
