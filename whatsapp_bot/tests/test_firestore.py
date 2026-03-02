"""Tests for Firestore session manager.

Fix C3: Tests call _execute_transaction directly (not via .__wrapped__)
because the transactional decorator is a pass-through lambda in conftest.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from whatsapp_bot.firestore_manager import SessionManager, SessionResult


class MockSnapshot:
    """Simulates a Firestore document snapshot for testing."""

    def __init__(self, exists: bool, data: dict | None = None):
        self._exists = exists
        self._data = data or {}

    @property
    def exists(self):
        return self._exists

    def to_dict(self):
        return self._data


class TestSessionTransaction:
    """Tests for the _execute_transaction static method."""

    def test_new_user_creates_session(self):
        """First-time user should get a new session with ai_active=True."""
        snapshot = MockSnapshot(exists=False)
        transaction = MagicMock()
        ref = MagicMock()
        ref.get.return_value = snapshot

        result = SessionManager._execute_transaction(
            transaction, ref, "34612345678"
        )

        assert result.is_new is True
        assert result.ai_active is True
        assert result.last_response_id is None
        assert result.timed_out is False
        transaction.set.assert_called_once()

    def test_existing_active_user(self):
        """Returning user with AI active should return existing session."""
        snapshot = MockSnapshot(
            exists=True,
            data={
                "ai_active": True,
                "last_response_id": "resp_prev",
                "last_interaction": datetime.now(timezone.utc),
            },
        )
        transaction = MagicMock()
        ref = MagicMock()
        ref.get.return_value = snapshot

        result = SessionManager._execute_transaction(
            transaction, ref, "34612345678"
        )

        assert result.is_new is False
        assert result.ai_active is True
        assert result.last_response_id == "resp_prev"
        assert result.timed_out is False
        transaction.update.assert_called_once()

    def test_ai_inactive_within_timeout(self):
        """Escalated user within 24h should remain in silent mode."""
        snapshot = MockSnapshot(
            exists=True,
            data={
                "ai_active": False,
                "last_response_id": "resp_prev",
                "last_interaction": datetime.now(timezone.utc)
                - timedelta(hours=1),
            },
        )
        transaction = MagicMock()
        ref = MagicMock()
        ref.get.return_value = snapshot

        result = SessionManager._execute_transaction(
            transaction, ref, "34612345678"
        )

        assert result.ai_active is False
        assert result.timed_out is False
        assert result.last_response_id == "resp_prev"

    def test_ai_inactive_past_timeout(self):
        """Escalated user past 24h should auto-reactivate AI."""
        snapshot = MockSnapshot(
            exists=True,
            data={
                "ai_active": False,
                "last_response_id": "resp_prev",
                "last_interaction": datetime.now(timezone.utc)
                - timedelta(hours=25),
            },
        )
        transaction = MagicMock()
        ref = MagicMock()
        ref.get.return_value = snapshot

        result = SessionManager._execute_transaction(
            transaction, ref, "34612345678"
        )

        assert result.ai_active is True
        assert result.timed_out is True

    def test_timezone_naive_timestamp_handled(self):
        """Firestore may return timezone-naive datetimes; should not crash."""
        naive_dt = datetime(2026, 1, 1, 12, 0, 0)  # No tzinfo
        snapshot = MockSnapshot(
            exists=True,
            data={
                "ai_active": True,
                "last_response_id": "resp_prev",
                "last_interaction": naive_dt,
            },
        )
        transaction = MagicMock()
        ref = MagicMock()
        ref.get.return_value = snapshot

        result = SessionManager._execute_transaction(
            transaction, ref, "34612345678"
        )

        assert result.ai_active is True
        assert result.is_new is False
