"""Storage abstraction for quotation memory backends."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx


@dataclass
class StoredQuotation:
    quotation_id: str
    timestamp: str
    payload: dict[str, Any]
    embedding: list[float]


@runtime_checkable
class MemoryStore(Protocol):
    async def save_quotation(self, payload: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
        ...

    async def retrieve_similar(self, embedding: list[float], limit: int) -> list[dict[str, Any]]:
        ...


class FileStore:
    """JSON file backed memory store used as default fallback backend."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load_items(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("items", []) if isinstance(raw, dict) else []

    def _save_items(self, items: list[dict[str, Any]]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=False, indent=2)

    async def save_quotation(self, payload: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
        items = self._load_items()
        record = StoredQuotation(
            quotation_id=f"Q-{uuid.uuid4().hex}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
            embedding=embedding,
        )
        items.append(record.__dict__)
        self._save_items(items)
        return {
            "quotation_id": record.quotation_id,
            "timestamp": record.timestamp,
            "status": "stored",
        }

    async def retrieve_similar(self, embedding: list[float], limit: int) -> list[dict[str, Any]]:
        if not embedding:
            return []
        items = self._load_items()
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in items:
            vector = item.get("embedding") or []
            if not isinstance(vector, list) or not vector:
                continue
            score = _cosine_similarity(embedding, [float(v) for v in vector])
            scored.append((score, item))
        scored.sort(key=lambda s: s[0], reverse=True)
        return [
            {
                "quotation_id": item["quotation_id"],
                "timestamp": item["timestamp"],
                "score": round(score, 4),
                "payload": item["payload"],
            }
            for score, item in scored[:limit]
        ]


class QdrantStore:
    """Qdrant-backed memory store with async HTTP client and context manager support."""

    def __init__(self, url: str, collection: str, timeout_seconds: float, api_key: str | None = None):
        self.url = url.rstrip("/")
        self.collection = collection
        self.timeout_seconds = timeout_seconds
        self._client: httpx.AsyncClient | None = None
        self._api_key = api_key
        self._sync_client: httpx.Client | None = None

    def _get_sync_client(self) -> httpx.Client:
        """Get or create synchronous client for startup healthchecks."""
        if self._sync_client is None:
            headers = {}
            if self._api_key is not None and self._api_key != "":
                headers["Api-Key"] = self._api_key
            self._sync_client = httpx.Client(headers=headers, timeout=self.timeout_seconds)
        return self._sync_client

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            headers = {}
            if self._api_key is not None and self._api_key != "":
                headers["Api-Key"] = self._api_key
            self._client = httpx.AsyncClient(headers=headers, timeout=self.timeout_seconds)
        return self._client

    def healthcheck(self) -> None:
        """Perform a synchronous health check against the Qdrant collections endpoint.

        This method uses a blocking HTTP client and is intended only for use during
        process startup/initialisation, before the main asyncio event loop is running.
        Do not call this method from within an active event loop.
        """
        client = self._get_sync_client()
        response = client.get(f"{self.url}/collections")
        response.raise_for_status()

    async def save_quotation(self, payload: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
        quotation_id = f"Q-{uuid.uuid4().hex}"
        timestamp = datetime.now(timezone.utc).isoformat()
        point = {
            "points": [
                {
                    "id": quotation_id,
                    "vector": embedding,
                    "payload": {
                        "quotation_id": quotation_id,
                        "timestamp": timestamp,
                        "data": payload,
                    },
                }
            ]
        }
        client = await self._get_client()
        response = await client.put(
            f"{self.url}/collections/{self.collection}/points",
            json=point,
        )
        response.raise_for_status()
        return {
            "quotation_id": quotation_id,
            "timestamp": timestamp,
            "status": "stored",
        }

    async def retrieve_similar(self, embedding: list[float], limit: int) -> list[dict[str, Any]]:
        query = {
            "vector": embedding,
            "limit": limit,
            "with_payload": True,
        }
        client = await self._get_client()
        response = await client.post(
            f"{self.url}/collections/{self.collection}/points/search",
            json=query,
        )
        response.raise_for_status()
        points = response.json().get("result", [])
        return [
            {
                "quotation_id": p.get("payload", {}).get("quotation_id", p.get("id")),
                "timestamp": p.get("payload", {}).get("timestamp"),
                "score": round(float(p.get("score", 0)), 4),
                "payload": p.get("payload", {}).get("data", {}),
            }
            for p in points
        ]

    async def close(self) -> None:
        """Close the underlying HTTP clients and release network resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None

    async def __aenter__(self) -> "QdrantStore":
        """Enable usage as an async context manager."""
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Ensure clients are closed when leaving an async context manager block."""
        await self.close()


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.
    
    If vectors have different dimensions, truncates to the shorter length.
    This truncation behavior can produce misleading similarity scores when
    comparing vectors of significantly different dimensions.
    
    Args:
        v1: First embedding vector.
        v2: Second embedding vector.
    
    Returns:
        Cosine similarity score between 0.0 and 1.0, or 0.0 if either vector is empty.
    """
    size = min(len(v1), len(v2))
    if size == 0:
        return 0.0
    a = v1[:size]
    b = v2[:size]
    numerator = sum(x * y for x, y in zip(a, b))
    den_a = math.sqrt(sum(x * x for x in a))
    den_b = math.sqrt(sum(y * y for y in b))
    if den_a == 0 or den_b == 0:
        return 0.0
    return numerator / (den_a * den_b)
