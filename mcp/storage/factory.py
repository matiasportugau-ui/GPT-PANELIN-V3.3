"""Memory store selection and startup validation."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.config.settings import load_runtime_settings
from mcp.storage.memory_store import FileStore, MemoryStore, QdrantStore

logger = logging.getLogger(__name__)


def initialize_memory_store() -> tuple[MemoryStore, dict[str, Any]]:
    settings = load_runtime_settings()
    flags = settings.feature_flags

    file_store = FileStore(settings.memory.file_store_path)
    metadata = {
        "active_backend": "file",
        "enable_vector_retrieval": flags.enable_vector_retrieval,
    }

    if not flags.enable_qdrant_memory:
        return file_store, metadata

    qdrant_store = QdrantStore(
        url=settings.memory.qdrant_url,
        collection=settings.memory.qdrant_collection,
        timeout_seconds=settings.memory.qdrant_timeout_seconds,
        api_key=settings.memory.qdrant_api_key,
    )
    try:
        qdrant_store.healthcheck()
        metadata["active_backend"] = "qdrant"
        return qdrant_store, metadata
    except Exception as exc:  # noqa: BLE001 - deliberate startup degrade behavior
        warning_payload = {
            "event": "memory_backend_degraded",
            "requested_backend": "qdrant",
            "active_backend": "file",
            "reason": str(exc),
        }
        logger.warning(json.dumps(warning_payload, ensure_ascii=False))
        return file_store, metadata
