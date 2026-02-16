"""Handler for quotation_store tool with backend-agnostic behavior.

Note: This module uses module-level global state (_memory_store, _enable_vector_retrieval)
to cache configuration. This is acceptable for single-server MCP instances but may cause
issues in multi-threaded or multi-process environments. For better testability and thread
safety in such environments, consider using dependency injection instead.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.storage.memory_store import MemoryStore

logger = logging.getLogger(__name__)

# Module-level state for backend configuration
_memory_store: MemoryStore | None = None
_enable_vector_retrieval = False
_backend_metadata: dict[str, Any] = {}

# Payload size limit (1MB JSON)
MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024


def configure_quotation_store(
    store: MemoryStore, 
    enable_vector_retrieval: bool,
    backend_metadata: dict[str, Any] | None = None,
) -> None:
    """Configure quotation store with backend and analytics metadata.
    
    Args:
        store: Memory store instance to use
        enable_vector_retrieval: Whether to enable vector similarity search
        backend_metadata: Optional metadata about backend selection for analytics
    """
    global _memory_store, _enable_vector_retrieval, _backend_metadata
    _memory_store = store
    _enable_vector_retrieval = enable_vector_retrieval
    _backend_metadata = backend_metadata or {}


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
    
    # Get backend type for analytics
    backend_type = _backend_metadata.get("active_backend", "unknown")
    
    # Store quotation with error handling and analytics
    try:
        store_result = await _memory_store.save_quotation(quotation, normalized_embedding)
        
        # Log successful storage with analytics
        analytics_payload = {
            "event": "quotation_stored",
            "backend": backend_type,
            "quotation_id": store_result["quotation_id"],
            "include_similar_requested": include_similar,
            "vector_retrieval_enabled": _enable_vector_retrieval,
        }
        logger.info(json.dumps(analytics_payload, ensure_ascii=False))
        
    except Exception as e:
        # Log storage failure with analytics
        error_payload = {
            "event": "quotation_store_failed",
            "backend": backend_type,
            "error_type": type(e).__name__,
            "error": str(e),
        }
        logger.error(json.dumps(error_payload, ensure_ascii=False))
        return {"error": f"Failed to store quotation: {e}"}

    # Retrieve similar quotations if requested
    similar: list[dict[str, Any]] = []
    if include_similar and _enable_vector_retrieval:
        try:
            # Clamp limit to valid range (schema defines 1-10)
            clamped_limit = max(1, min(limit, 10))
            similar = await _memory_store.retrieve_similar(normalized_embedding, clamped_limit)
            
            # Log successful retrieval with analytics
            retrieval_payload = {
                "event": "similar_quotations_retrieved",
                "backend": backend_type,
                "quotation_id": store_result["quotation_id"],
                "similar_count": len(similar),
                "requested_limit": clamped_limit,
            }
            logger.info(json.dumps(retrieval_payload, ensure_ascii=False))
            
        except Exception as e:
            # Log retrieval failure with analytics
            retrieval_error_payload = {
                "event": "similar_quotations_retrieval_failed",
                "backend": backend_type,
                "quotation_id": store_result["quotation_id"],
                "error_type": type(e).__name__,
                "error": str(e),
            }
            logger.warning(json.dumps(retrieval_error_payload, ensure_ascii=False))
            
            # Non-fatal: return stored quotation even if retrieval fails
            return {
                "message": "Quotation stored successfully, but similarity search failed",
                "quotation_id": store_result["quotation_id"],
                "timestamp": store_result["timestamp"],
                "similar_quotations": [],
                "retrieval_error": str(e),
                "backend_info": {
                    "active_backend": backend_type,
                    "vector_retrieval_enabled": _enable_vector_retrieval,
                },
            }

    return {
        "message": "Quotation stored successfully",
        "quotation_id": store_result["quotation_id"],
        "timestamp": store_result["timestamp"],
        "similar_quotations": similar,
        "backend_info": {
            "active_backend": backend_type,
            "vector_retrieval_enabled": _enable_vector_retrieval,
        },
    }
