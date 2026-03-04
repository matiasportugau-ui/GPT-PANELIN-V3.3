"""Memory store selection and startup validation."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from panelin_mcp_server.config.settings import load_runtime_settings
from panelin_mcp_server.storage.memory_store import FileStore, MemoryStore, QdrantStore

logger = logging.getLogger(__name__)


def initialize_memory_store() -> tuple[MemoryStore, dict[str, Any]]:
    """Initialize memory store with analytics and structured logging.
    
    Returns:
        tuple: (MemoryStore instance, metadata dict with analytics)
    """
    settings = load_runtime_settings()
    flags = settings.feature_flags

    # Initialize file store as fallback
    file_store = FileStore(settings.memory.file_store_path)
    
    # Base metadata with analytics
    metadata = {
        "active_backend": "file",
        "enable_vector_retrieval": flags.enable_vector_retrieval,
        "selection_analytics": {
            "requested_backend": "file" if not flags.enable_qdrant_memory else "qdrant",
            "selection_reason": "default",
        },
    }

    # If Qdrant is not enabled, return file store immediately
    if not flags.enable_qdrant_memory:
        analytics_payload = {
            "event": "memory_backend_selected",
            "backend": "file",
            "reason": "qdrant_disabled_in_config",
            "enable_vector_retrieval": flags.enable_vector_retrieval,
        }
        logger.info(json.dumps(analytics_payload, ensure_ascii=False))
        metadata["selection_analytics"]["selection_reason"] = "qdrant_disabled_in_config"
        return file_store, metadata

    # Initialize Qdrant store and perform health check
    qdrant_store = QdrantStore(
        url=settings.memory.qdrant_url,
        collection=settings.memory.qdrant_collection,
        timeout_seconds=settings.memory.qdrant_timeout_seconds,
        api_key=settings.memory.qdrant_api_key,
    )
    
    try:
        qdrant_store.healthcheck()
        # Qdrant is healthy, use it
        metadata["active_backend"] = "qdrant"
        metadata["selection_analytics"].update({
            "selection_reason": "qdrant_healthy",
            "qdrant_url": settings.memory.qdrant_url,
            "qdrant_collection": settings.memory.qdrant_collection,
        })
        
        analytics_payload = {
            "event": "memory_backend_selected",
            "backend": "qdrant",
            "reason": "qdrant_healthy",
            "qdrant_url": settings.memory.qdrant_url,
            "qdrant_collection": settings.memory.qdrant_collection,
            "enable_vector_retrieval": flags.enable_vector_retrieval,
        }
        logger.info(json.dumps(analytics_payload, ensure_ascii=False))
        return qdrant_store, metadata
        
    except httpx.ConnectError as exc:
        # Network connection failed
        degradation_payload = {
            "event": "memory_backend_degraded",
            "requested_backend": "qdrant",
            "active_backend": "file",
            "error_type": "connection_error",
            "reason": str(exc),
            "qdrant_url": settings.memory.qdrant_url,
        }
        logger.warning(json.dumps(degradation_payload, ensure_ascii=False))
        metadata["selection_analytics"].update({
            "selection_reason": "qdrant_connection_failed",
            "error_type": "connection_error",
            "error_detail": str(exc),
        })
        return file_store, metadata
        
    except httpx.TimeoutException as exc:
        # Timeout during health check
        degradation_payload = {
            "event": "memory_backend_degraded",
            "requested_backend": "qdrant",
            "active_backend": "file",
            "error_type": "timeout_error",
            "reason": str(exc),
            "timeout_seconds": settings.memory.qdrant_timeout_seconds,
        }
        logger.warning(json.dumps(degradation_payload, ensure_ascii=False))
        metadata["selection_analytics"].update({
            "selection_reason": "qdrant_timeout",
            "error_type": "timeout_error",
            "timeout_seconds": settings.memory.qdrant_timeout_seconds,
        })
        return file_store, metadata
        
    except Exception as exc:
        # Other health check failures
        degradation_payload = {
            "event": "memory_backend_degraded",
            "requested_backend": "qdrant",
            "active_backend": "file",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }
        logger.warning(json.dumps(degradation_payload, ensure_ascii=False))
        metadata["selection_analytics"].update({
            "selection_reason": "qdrant_health_check_failed",
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
        })
        return file_store, metadata
