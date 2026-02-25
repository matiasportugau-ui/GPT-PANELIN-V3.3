"""Tests for the Sheets client module (cache, mock API)."""

from __future__ import annotations

import time

import pytest

from panelin_sheets_orchestrator.sheets_client import SnapshotCache


class TestSnapshotCache:
    def test_put_and_get(self):
        cache = SnapshotCache(ttl_seconds=60)
        cache.put("key1", {"data": "hello"})
        assert cache.get("key1") == {"data": "hello"}

    def test_cache_miss(self):
        cache = SnapshotCache(ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = SnapshotCache(ttl_seconds=0)
        cache.put("key1", {"data": "hello"})
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_invalidate(self):
        cache = SnapshotCache(ttl_seconds=60)
        cache.put("sid1|range1", {"v": 1})
        cache.put("sid1|range2", {"v": 2})
        cache.put("sid2|range1", {"v": 3})
        cache.invalidate("sid1")
        assert cache.get("sid1|range1") is None
        assert cache.get("sid1|range2") is None
        assert cache.get("sid2|range1") is not None

    def test_clear(self):
        cache = SnapshotCache(ttl_seconds=60)
        cache.put("a", {"v": 1})
        cache.put("b", {"v": 2})
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_overwrite(self):
        cache = SnapshotCache(ttl_seconds=60)
        cache.put("key1", {"v": 1})
        cache.put("key1", {"v": 2})
        assert cache.get("key1") == {"v": 2}

    def test_max_entries_eviction(self):
        """Cache should evict oldest entry when max_entries is reached."""
        cache = SnapshotCache(ttl_seconds=60, max_entries=3)
        cache.put("a", {"v": 1})
        time.sleep(0.001)
        cache.put("b", {"v": 2})
        time.sleep(0.001)
        cache.put("c", {"v": 3})
        assert len(cache) == 3

        cache.put("d", {"v": 4})
        assert len(cache) == 3
        assert cache.get("a") is None
        assert cache.get("d") == {"v": 4}

    def test_max_entries_no_eviction_on_update(self):
        """Updating existing key should not trigger eviction."""
        cache = SnapshotCache(ttl_seconds=60, max_entries=2)
        cache.put("a", {"v": 1})
        cache.put("b", {"v": 2})
        cache.put("a", {"v": 99})
        assert len(cache) == 2
        assert cache.get("a") == {"v": 99}
        assert cache.get("b") == {"v": 2}

    def test_len(self):
        cache = SnapshotCache(ttl_seconds=60)
        assert len(cache) == 0
        cache.put("a", {"v": 1})
        assert len(cache) == 1
