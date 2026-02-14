"""Centralized runtime configuration for MCP server feature flags and memory providers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_FILE = Path(__file__).with_name("mcp_server_config.json")


@dataclass(frozen=True)
class FeatureFlags:
    enable_qdrant_memory: bool
    enable_vector_retrieval: bool


@dataclass(frozen=True)
class MemoryConfig:
    file_store_path: Path
    qdrant_url: str
    qdrant_api_key: str | None
    qdrant_collection: str
    qdrant_timeout_seconds: float


@dataclass(frozen=True)
class RuntimeSettings:
    feature_flags: FeatureFlags
    memory: MemoryConfig



def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}



def load_runtime_settings() -> RuntimeSettings:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    flags = config.get("feature_flags", {})
    memory = config.get("memory", {})
    qdrant = memory.get("qdrant", {})

    enable_qdrant_default = _as_bool(flags.get("ENABLE_QDRANT_MEMORY"), False)
    enable_retrieval_default = _as_bool(flags.get("ENABLE_VECTOR_RETRIEVAL"), False)

    enable_qdrant_memory = _as_bool(os.getenv("ENABLE_QDRANT_MEMORY"), enable_qdrant_default)
    enable_vector_retrieval = _as_bool(os.getenv("ENABLE_VECTOR_RETRIEVAL"), enable_retrieval_default)

    file_store_relative = memory.get("file_store_path", "../quotation_memory.json")
    
    # Resolve the file store path relative to the config file, but guard against
    # path traversal outside the expected configuration root directory.
    # We treat the parent of the config directory as the allowed root so that
    # the existing default ("../quotation_memory.json") remains valid.
    base_dir = CONFIG_FILE.parent.parent.resolve()
    file_store_relative_path = Path(file_store_relative)
    
    if file_store_relative_path.is_absolute():
        raise ValueError(f"Invalid file_store_path '{file_store_relative}': absolute paths are not allowed.")
    
    file_store_path = (CONFIG_FILE.parent / file_store_relative_path).resolve()
    try:
        # Ensure the resolved path is within the allowed base directory.
        file_store_path.relative_to(base_dir)
    except ValueError:
        raise ValueError(
            f"Invalid file_store_path '{file_store_relative}': path traversal outside '{base_dir}' is not allowed."
        )

    api_key_env = qdrant.get("api_key_env", "QDRANT_API_KEY")
    qdrant_api_key = os.getenv(api_key_env)

    return RuntimeSettings(
        feature_flags=FeatureFlags(
            enable_qdrant_memory=enable_qdrant_memory,
            enable_vector_retrieval=enable_vector_retrieval,
        ),
        memory=MemoryConfig(
            file_store_path=file_store_path,
            qdrant_url=os.getenv("QDRANT_URL", qdrant.get("url", "http://localhost:6333")),
            qdrant_api_key=qdrant_api_key,
            qdrant_collection=os.getenv("QDRANT_COLLECTION", qdrant.get("collection", "panelin_quotations")),
            qdrant_timeout_seconds=float(qdrant.get("timeout_seconds", 2)),
        ),
    )
