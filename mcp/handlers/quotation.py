"""Handler for quotation_store tool with backend-agnostic behavior."""

from __future__ import annotations

from typing import Any

from mcp.storage.memory_store import MemoryStore

_memory_store: MemoryStore | None = None
_enable_vector_retrieval = False


def configure_quotation_store(store: MemoryStore, enable_vector_retrieval: bool) -> None:
    global _memory_store, _enable_vector_retrieval
    _memory_store = store
    _enable_vector_retrieval = enable_vector_retrieval


async def handle_quotation_store(arguments: dict[str, Any]) -> dict[str, Any]:
    if _memory_store is None:
        return {"error": "quotation_store backend is not configured"}

    quotation = arguments.get("quotation")
    embedding = arguments.get("embedding")
    include_similar = bool(arguments.get("include_similar", False))
    limit = int(arguments.get("limit", 3))

    if not isinstance(quotation, dict):
        return {"error": "quotation (object) is required"}
    if not isinstance(embedding, list) or not embedding:
        return {"error": "embedding (number[]) is required"}

    normalized_embedding = [float(x) for x in embedding]
    store_result = await _memory_store.save_quotation(quotation, normalized_embedding)

    similar: list[dict[str, Any]] = []
    if include_similar and _enable_vector_retrieval:
        similar = await _memory_store.retrieve_similar(normalized_embedding, max(1, min(limit, 10)))

    return {
        "message": "Quotation stored successfully",
        "quotation_id": store_result["quotation_id"],
        "timestamp": store_result["timestamp"],
        "similar_quotations": similar,
    }
