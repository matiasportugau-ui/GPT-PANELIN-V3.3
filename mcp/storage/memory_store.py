"""Storage abstraction for quotation memory backends."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import requests


@dataclass
class StoredQuotation:
    quotation_id: str
    timestamp: str
    payload: dict[str, Any]
    embedding: list[float]


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
            quotation_id=f"Q-{uuid.uuid4().hex[:10]}",
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    """Qdrant-backed memory store."""

    def __init__(self, url: str, collection: str, timeout_seconds: float, api_key: str | None = None):
        self.url = url.rstrip("/")
        self.collection = collection
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"api-key": api_key})

    def healthcheck(self) -> None:
        response = self.session.get(f"{self.url}/collections", timeout=self.timeout_seconds)
        response.raise_for_status()

    async def save_quotation(self, payload: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
        quotation_id = f"Q-{uuid.uuid4().hex[:10]}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        response = self.session.put(
            f"{self.url}/collections/{self.collection}/points",
            json=point,
            timeout=self.timeout_seconds,
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
        response = self.session.post(
            f"{self.url}/collections/{self.collection}/points/search",
            json=query,
            timeout=self.timeout_seconds,
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


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
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
