"""Truncated exponential backoff with jitter for transient API errors.

Formula: delay = min(base_delay × 2^attempt + uniform(0, base_delay), max_delay)

Retries only on:
- httpx.TimeoutException (network timeouts)
- httpx.HTTPStatusError with status 429, 500, 502, 503, 504
- openai.RateLimitError (429 from OpenAI)
- openai.APITimeoutError (OpenAI request timeout)

Non-retryable errors (400, 401, 403, 404, 422) propagate immediately.
Jitter prevents synchronized retry storms across multiple Cloud Run instances.
"""

import asyncio
import logging
import random
from typing import Any, Callable

import httpx
import openai

logger = logging.getLogger(__name__)

RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is transient and retryable.

    Args:
        exc: The exception to evaluate.

    Returns:
        True if the error is transient and the operation should be retried.
    """
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_HTTP_CODES
    if isinstance(exc, (openai.RateLimitError, openai.APITimeoutError)):
        return True
    return False


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs: Any,
) -> Any:
    """Execute an async function with exponential backoff on transient failures.

    The delay between retries follows truncated exponential backoff with
    uniform jitter to prevent thundering herds:

        delay(attempt) = min(base_delay × 2^attempt + uniform(0, base_delay), max_delay)

    Resulting delays (with base_delay=1.0):
        Attempt 0: 1.0 - 2.0 seconds
        Attempt 1: 2.0 - 3.0 seconds
        Attempt 2: 4.0 - 5.0 seconds
        Attempt 3: 8.0 - 9.0 seconds
        Attempt 4: 16.0 - 17.0 seconds

    Args:
        func: Async callable to execute.
        *args: Positional arguments for func.
        max_retries: Maximum number of retry attempts (0 = no retries).
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap in seconds.
        **kwargs: Keyword arguments for func.

    Returns:
        The return value of func on success.

    Raises:
        The last exception if all retries are exhausted, or immediately
        if the exception is non-retryable (e.g. 400 Bad Request).
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc

            if not _is_retryable(exc):
                raise

            if attempt >= max_retries:
                logger.error(
                    "All %d retries exhausted for %s: %s",
                    max_retries,
                    getattr(func, "__name__", "unknown"),
                    exc,
                )
                raise

            jitter = random.uniform(0, base_delay)
            delay = min(base_delay * (2 ** attempt) + jitter, max_delay)
            logger.warning(
                "Retry %d/%d for %s after %.1fs (error: %s)",
                attempt + 1,
                max_retries,
                getattr(func, "__name__", "unknown"),
                delay,
                exc,
            )
            await asyncio.sleep(delay)

    # Should never reach here, but satisfies type checker
    if last_exception:
        raise last_exception
    raise RuntimeError("retry_with_backoff: unexpected state")
