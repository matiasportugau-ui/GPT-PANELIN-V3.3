"""Firestore session manager for WhatsApp conversation state.

Schema (collection: 'sessions', document ID: wa_id):
    wa_id: str               — WhatsApp phone number
    last_response_id: str    — OpenAI Response ID for conversation chaining
    ai_active: bool          — True = AI handles, False = human agent handles
    last_interaction: datetime — UTC timestamp of last activity
    lead_id: str | None      — Wolf API customer ID (optional)

Concurrency: Uses Firestore transactions to prevent race conditions
when multiple webhooks arrive simultaneously for the same user.

CRITICAL: No external API calls (OpenAI, WhatsApp, etc.) inside
transactions. Transactions may retry multiple times on contention
(up to 5 attempts). All side effects must be idempotent.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1 import transaction as fs_transaction

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sessions"


@dataclass
class SessionResult:
    """Result of a session lookup/creation operation."""

    last_response_id: str | None  # None for brand-new sessions
    ai_active: bool
    is_new: bool       # True if session was just created
    timed_out: bool    # True if human escalation timed out and AI resumed


class SessionManager:
    """Manages WhatsApp conversation sessions in Firestore.

    All public methods are synchronous (firebase-admin SDK is sync).
    Callers in async contexts should use starlette.concurrency.run_in_threadpool().
    """

    def __init__(self, timeout_hours: int = 24):
        """Initialize the session manager.

        Args:
            timeout_hours: Hours of inactivity after human escalation
                           before AI automatically resumes control.
                           Defaults to 24 (aligns with WhatsApp service window).
        """
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        self._db = firestore.client()
        self._timeout_hours = timeout_hours

    @property
    def db(self):
        """Expose Firestore client for use by vector_store_sync (index storage)."""
        return self._db

    def get_or_create_session(self, wa_id: str) -> SessionResult:
        """Get existing session or create new one, transactionally.

        Behavior:
        - New user: Creates session with ai_active=True, returns is_new=True.
        - Existing, AI active: Updates last_interaction, returns session.
        - Existing, AI inactive, within timeout: Returns ai_active=False (silent).
        - Existing, AI inactive, past timeout: Resets ai_active=True, timed_out=True.

        Args:
            wa_id: WhatsApp phone number (unique identifier).

        Returns:
            SessionResult with current session state.
        """
        ref = self._db.collection(COLLECTION_NAME).document(wa_id)
        txn = self._db.transaction()
        return self._execute_transaction(txn, ref, wa_id)

    @staticmethod
    @fs_transaction.transactional
    def _execute_transaction(
        transaction,
        ref,
        wa_id: str,
    ) -> SessionResult:
        """Atomic read-modify-write for session state.

        This is a @staticmethod because @fs_transaction.transactional
        requires the transaction as the first positional argument.

        The 24h timeout is hardcoded because static methods cannot
        reference instance attributes. This aligns with WhatsApp's
        24h service window.
        """
        snapshot = ref.get(transaction=transaction)
        now = datetime.now(timezone.utc)

        if snapshot.exists:
            data = snapshot.to_dict()
            ai_active = data.get("ai_active", True)
            last_interaction = data.get("last_interaction", now)
            last_response_id = data.get("last_response_id")
            timed_out = False

            # Handle timezone-naive timestamps from Firestore
            if hasattr(last_interaction, "tzinfo") and last_interaction.tzinfo is None:
                last_interaction = last_interaction.replace(tzinfo=timezone.utc)

            if not ai_active:
                time_diff = now - last_interaction
                if time_diff > timedelta(hours=24):
                    # Timeout expired — reactivate AI
                    ai_active = True
                    timed_out = True
                else:
                    # Human still handling — update timestamp, return silent
                    transaction.update(ref, {"last_interaction": now})
                    return SessionResult(
                        last_response_id=last_response_id,
                        ai_active=False,
                        is_new=False,
                        timed_out=False,
                    )

            transaction.update(ref, {
                "last_interaction": now,
                "ai_active": ai_active,
            })
            return SessionResult(
                last_response_id=last_response_id,
                ai_active=ai_active,
                is_new=False,
                timed_out=timed_out,
            )

        else:
            # Brand-new user — create session
            transaction.set(ref, {
                "wa_id": wa_id,
                "last_response_id": None,
                "ai_active": True,
                "last_interaction": now,
                "lead_id": None,
            })
            return SessionResult(
                last_response_id=None,
                ai_active=True,
                is_new=True,
                timed_out=False,
            )

    def update_response_id(self, wa_id: str, response_id: str) -> None:
        """Store the latest OpenAI response ID for conversation chaining.

        Called after each successful OpenAI response to enable
        previous_response_id chaining on the next turn.
        """
        self._db.collection(COLLECTION_NAME).document(wa_id).update({
            "last_response_id": response_id,
        })

    def set_ai_inactive(self, wa_id: str) -> None:
        """Pause AI and transfer control to human agent.

        Sets ai_active=False and updates last_interaction timestamp.
        The AI will auto-resume after 24h of inactivity (timeout).
        """
        now = datetime.now(timezone.utc)
        self._db.collection(COLLECTION_NAME).document(wa_id).update({
            "ai_active": False,
            "last_interaction": now,
        })

    def update_lead_id(self, wa_id: str, lead_id: str) -> None:
        """Store the Wolf API customer ID for cross-referencing."""
        self._db.collection(COLLECTION_NAME).document(wa_id).update({
            "lead_id": lead_id,
        })
