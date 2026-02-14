"""Handler for quotation_store tool with backend-agnostic behavior.

Note: This module uses module-level global state (_memory_store, _enable_vector_retrieval)
to cache configuration. This is acceptable for single-server MCP instances but may cause
issues in multi-threaded or multi-process environments. For better testability and thread
safety in such environments, consider using dependency injection instead.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.storage.memory_store import MemoryStore

# Module-level state for backend configuration
_memory_store: MemoryStore | None = None
_enable_vector_retrieval = False

# Payload size limit (1MB JSON)
MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024


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

    # Validate quotation payload
    if not isinstance(quotation, dict):
        return {"error": "quotation (object) is required"}
    
    # Validate embedding
    if not isinstance(embedding, list):
        return {"error": "embedding (number[]) is required"}
    if not embedding:
        return {"error": "embedding (non-empty number[]) is required; empty array provided"}
    
    # Validate quotation size to prevent resource exhaustion
    try:
        serialized = json.dumps(quotation, ensure_ascii=False)
        if len(serialized.encode("utf-8")) > MAX_PAYLOAD_SIZE_BYTES:
            return {"error": f"quotation payload exceeds maximum size of {MAX_PAYLOAD_SIZE_BYTES} bytes"}
    except (TypeError, ValueError) as e:
        return {"error": f"quotation payload is not JSON-serializable: {e}"}

    normalized_embedding = [float(x) for x in embedding]
    
    # Store quotation with error handling
    try:
        store_result = await _memory_store.save_quotation(quotation, normalized_embedding)
    except Exception as e:
        return {"error": f"Failed to store quotation: {e}"}

    # Retrieve similar quotations if requested
    similar: list[dict[str, Any]] = []
    if include_similar and _enable_vector_retrieval:
        try:
            # Clamp limit to valid range (schema defines 1-10)
            clamped_limit = max(1, min(limit, 10))
            similar = await _memory_store.retrieve_similar(normalized_embedding, clamped_limit)
        except Exception as e:
            # Non-fatal: return stored quotation even if retrieval fails
            return {
                "message": "Quotation stored successfully, but similarity search failed",
                "quotation_id": store_result["quotation_id"],
                "timestamp": store_result["timestamp"],
                "similar_quotations": [],
                "retrieval_error": str(e),
            }

    return {
        "message": "Quotation stored successfully",
        "quotation_id": store_result["quotation_id"],
        "timestamp": store_result["timestamp"],
        "similar_quotations": similar,
    }
