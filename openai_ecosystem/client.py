"""Helpers for normalizing OpenAI response payloads.

These utilities are intentionally defensive: SDK payloads can arrive as dicts,
Pydantic models, or ad-hoc objects depending on transport and API family.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read `key` from dict-like or object-like values."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_plain(value: Any) -> Any:
    """Convert SDK/dataclass-ish objects into JSON-friendly primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {
            k: _to_plain(v)
            for k, v in value.__dict__.items()
            if not k.startswith("_")
        }
    return str(value)


def _iter_output_items(response: Any) -> list[Any]:
    """Collect candidate output/message items across API variants."""
    candidates = [
        _get(response, "output"),
        _get(response, "items"),
        _get(response, "messages"),
        _get(_get(response, "message"), "content"),
    ]

    # Chat Completions shape.
    choices = _get(response, "choices")
    if choices:
        for choice in choices:
            message = _get(choice, "message") or {}
            candidates.append(_get(message, "content"))
            candidates.append(message)

    items: list[Any] = []
    for candidate in candidates:
        if not candidate:
            continue
        if isinstance(candidate, list):
            items.extend(candidate)
        else:
            items.append(candidate)
    return items


def _extract_text_from_item(item: Any) -> list[str]:
    """Extract text snippets from one item/content block."""
    snippets: list[str] = []

    if isinstance(item, str):
        return [item]

    # Structured content arrays: [{"type":"text","text":"..."}, ...]
    content = _get(item, "content")
    if isinstance(content, list):
        for part in content:
            part_type = (_get(part, "type") or "").lower()
            if part_type in {"output_text", "text", "message_text", "input_text"}:
                text = _get(part, "text")
                if isinstance(text, str) and text.strip():
                    snippets.append(text)
                # Some SDKs nest actual text in a `value` key.
                value = _get(part, "value")
                if isinstance(value, str) and value.strip():
                    snippets.append(value)
            elif part_type in {"message"}:
                nested = _extract_text_from_item(part)
                snippets.extend(nested)

    # Direct text-bearing keys on objects.
    for key in ("output_text", "text", "value", "content", "message"):
        value = _get(item, key)
        if isinstance(value, str) and value.strip():
            snippets.append(value)

    # Chat-completions tool result style: {"type":"text","text":"..."}
    item_type = (_get(item, "type") or "").lower()
    if item_type in {"output_text", "text", "message_text"}:
        value = _get(item, "text") or _get(item, "value")
        if isinstance(value, str) and value.strip():
            snippets.append(value)

    return snippets


def _diagnostic_summary(response: Any) -> str:
    """Produce a compact shape summary when no text payload can be extracted."""
    item_types: list[str] = []
    content_types: list[str] = []

    for item in _iter_output_items(response):
        item_type = _get(item, "type")
        if item_type:
            item_types.append(str(item_type))

        content = _get(item, "content")
        if isinstance(content, list):
            for part in content:
                part_type = _get(part, "type")
                if part_type:
                    content_types.append(str(part_type))

    if not item_types and not content_types:
        top_keys = []
        if isinstance(response, dict):
            top_keys = sorted(response.keys())[:8]
        else:
            data = _to_plain(response)
            if isinstance(data, dict):
                top_keys = sorted(data.keys())[:8]
        return f"[no text content; top-level keys={top_keys}]"

    item_s = ",".join(sorted(set(item_types))) or "none"
    content_s = ",".join(sorted(set(content_types))) or "none"
    return f"[no text content; item_types={item_s}; content_types={content_s}]"


def extract_text(response: Any) -> str:
    """Return normalized text from OpenAI responses.

    Supported shapes include:
    - Responses API (`output_text`, `output[]` with nested `content[]` parts)
    - Chat Completions (`choices[].message.content` as str or part list)
    - Message-centric variants (`message.content`, `messages[]`)

    If no text is available, returns a compact diagnostic summary string.
    """
    direct = _get(response, "output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    snippets: list[str] = []
    for item in _iter_output_items(response):
        snippets.extend(_extract_text_from_item(item))

    normalized: list[str] = []
    seen: set[str] = set()
    for snippet in snippets:
        if not isinstance(snippet, str):
            continue
        cleaned = snippet.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    if normalized:
        return "\n".join(normalized)

    return _diagnostic_summary(response)


def extract_primary_output(response: Any) -> dict[str, Any]:
    """Return the primary payload as text, structured data, or tool-call metadata.

    The result has shape:
    - {"type": "text", "value": str}
    - {"type": "structured", "value": <json-friendly object>}
    - {"type": "tool_call", "value": {"name": ..., "arguments": ...}}
    - {"type": "unknown", "value": None, "diagnostic": ...}
    """
    text = extract_text(response)
    if text and not text.startswith("[no text content;"):
        return {"type": "text", "value": text}

    # Structured/parsed variants across SDK families.
    for key in ("output_parsed", "parsed", "response", "data"):
        value = _get(response, key)
        if isinstance(value, (dict, list)) and value:
            return {"type": "structured", "value": _to_plain(value)}

    # Search first output item with explicit tool metadata.
    for item in _iter_output_items(response):
        item_type = (_get(item, "type") or "").lower()
        if "tool" in item_type or "function" in item_type:
            return {
                "type": "tool_call",
                "value": {
                    "name": _get(item, "name") or _get(item, "tool_name"),
                    "arguments": _to_plain(
                        _get(item, "arguments") or _get(item, "input") or {}
                    ),
                    "id": _get(item, "id"),
                },
            }

    # Some chat APIs place tool calls under message.tool_calls.
    tool_calls = _get(_get(response, "message"), "tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        first = tool_calls[0]
        function = _get(first, "function") or {}
        return {
            "type": "tool_call",
            "value": {
                "name": _get(function, "name") or _get(first, "name"),
                "arguments": _to_plain(
                    _get(function, "arguments") or _get(first, "arguments") or {}
                ),
                "id": _get(first, "id"),
            },
        }

    return {"type": "unknown", "value": None, "diagnostic": _diagnostic_summary(response)}
