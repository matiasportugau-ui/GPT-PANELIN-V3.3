"""Observability utilities for MCP tool invocation telemetry."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path("observability/logs/tool_invocations.ndjson")


@dataclass(frozen=True)
class ToolInvocationContext:
    """Context describing a single tool invocation lifecycle."""

    session_id: str
    tool_name: str
    request_id: str
    cache_status: str | None = None


class JsonLineFormatter(logging.Formatter):
    """Formatter that writes logging records as compact JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
            "tool_name": getattr(record, "tool_name", None),
            "request_id": getattr(record, "request_id", None),
            "session_id": getattr(record, "session_id", None),
            "latency_ms": getattr(record, "latency_ms", None),
            "cache_status": getattr(record, "cache_status", None),
            "token_input": getattr(record, "token_input", None),
            "token_output": getattr(record, "token_output", None),
            "error_code": getattr(record, "error_code", None),
        }
        return json.dumps(payload, ensure_ascii=False)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("mcp.observability")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    log_path = Path(os.environ.get("MCP_TOOL_LOG_PATH", DEFAULT_LOG_PATH))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonLineFormatter())
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


LOGGER = _build_logger()


def get_invocation_context(tool_name: str, arguments: dict[str, Any]) -> ToolInvocationContext:
    """Create invocation context using known argument keys, with safe defaults."""
    session_id = (
        str(arguments.get("session_id"))
        if arguments.get("session_id")
        else str(arguments.get("client_id") or "unknown")
    )
    request_id = (
        str(arguments.get("request_id"))
        if arguments.get("request_id")
        else f"req-{int(time.time() * 1000)}"
    )
    cache_status = arguments.get("cache_status")
    return ToolInvocationContext(
        session_id=session_id,
        tool_name=tool_name,
        request_id=request_id,
        cache_status=str(cache_status) if cache_status else None,
    )


def log_tool_invocation_start(context: ToolInvocationContext, token_input: int | None) -> float:
    """Log start event and return monotonic timer for duration measurement."""
    start_time = time.perf_counter()
    LOGGER.info(
        "tool invocation started",
        extra={
            "event": "tool_invocation_start",
            "tool_name": context.tool_name,
            "request_id": context.request_id,
            "session_id": context.session_id,
            "cache_status": context.cache_status,
            "token_input": token_input,
        },
    )
    return start_time


def log_tool_invocation_success(
    context: ToolInvocationContext,
    start_time: float,
    token_input: int | None,
    token_output: int | None,
) -> None:
    """Log successful completion with latency and token totals."""
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    LOGGER.info(
        "tool invocation completed",
        extra={
            "event": "tool_invocation_success",
            "tool_name": context.tool_name,
            "request_id": context.request_id,
            "session_id": context.session_id,
            "latency_ms": latency_ms,
            "cache_status": context.cache_status,
            "token_input": token_input,
            "token_output": token_output,
        },
    )


def log_tool_invocation_error(
    context: ToolInvocationContext,
    start_time: float,
    error_code: str,
    token_input: int | None,
) -> None:
    """Log failed completion with latency and normalized error code."""
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    LOGGER.error(
        "tool invocation failed",
        extra={
            "event": "tool_invocation_error",
            "tool_name": context.tool_name,
            "request_id": context.request_id,
            "session_id": context.session_id,
            "latency_ms": latency_ms,
            "cache_status": context.cache_status,
            "token_input": token_input,
            "error_code": error_code,
        },
    )
