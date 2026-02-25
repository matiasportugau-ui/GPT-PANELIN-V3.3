"""Shared test fixtures for WhatsApp Bot tests.

Mocks firebase_admin and google.cloud dependencies to avoid
requiring GCP credentials in the test environment.

Fix C3: The transactional mock uses a pass-through lambda (not MagicMock)
to preserve the actual _execute_transaction function logic in tests.
"""

import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set test env vars before any imports
os.environ.setdefault("VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("META_APP_SECRET", "test-app-secret")
os.environ.setdefault("WHATSAPP_TOKEN", "test-whatsapp-token")
os.environ.setdefault("PHONE_NUMBER_ID", "123456789")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("VECTOR_STORE_ID", "vs_test123")
os.environ.setdefault("SYNC_API_KEY", "test-sync-key")

# ── Mock firebase_admin ──────────────────────────────────────
_mock_firebase = MagicMock()
_mock_firebase.initialize_app = MagicMock()
_mock_firebase._apps = {"[DEFAULT]": MagicMock()}
sys.modules["firebase_admin"] = _mock_firebase

_mock_firebase_firestore = MagicMock()
sys.modules["firebase_admin.firestore"] = _mock_firebase_firestore

# ── Mock google.cloud.firestore_v1 (Fix C3) ──────────────────
# Use pass-through decorator so _execute_transaction retains its logic
_mock_fs_v1_transaction = types.ModuleType("google.cloud.firestore_v1.transaction")
_mock_fs_v1_transaction.transactional = lambda fn: fn  # Pass-through, not MagicMock
_mock_fs_v1_transaction.Transaction = MagicMock

_mock_fs_v1 = types.ModuleType("google.cloud.firestore_v1")
_mock_fs_v1.transaction = _mock_fs_v1_transaction

sys.modules["google.cloud.firestore_v1"] = _mock_fs_v1
sys.modules["google.cloud.firestore_v1.transaction"] = _mock_fs_v1_transaction

# Ensure google and google.cloud parent modules exist
if "google" not in sys.modules:
    sys.modules["google"] = types.ModuleType("google")
if "google.cloud" not in sys.modules:
    sys.modules["google.cloud"] = types.ModuleType("google.cloud")


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def settings():
    """Test settings instance."""
    from whatsapp_bot.config import load_settings
    return load_settings()


@pytest.fixture
def mock_wa_client():
    """Mock WhatsApp client with async methods."""
    client = MagicMock()
    client.send_text = AsyncMock(return_value=200)
    client.send_document = AsyncMock(return_value=200)
    client.send_template = AsyncMock(return_value=200)
    client.send_text_or_template = AsyncMock(return_value=200)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service with async send_message."""
    from whatsapp_bot.openai_service import ResponseResult

    service = MagicMock()
    service.send_message = AsyncMock(
        return_value=ResponseResult(
            text="Tenemos un ático en Marbella por 285.000 EUR.",
            response_id="resp_abc123",
            should_send_pdf=False,
        )
    )
    service.detect_escalation_intent = MagicMock(return_value=False)
    return service


@pytest.fixture
def mock_session_manager():
    """Mock session manager with sync methods."""
    from whatsapp_bot.firestore_manager import SessionResult

    manager = MagicMock()
    manager.get_or_create_session = MagicMock(
        return_value=SessionResult(
            last_response_id="resp_previous",
            ai_active=True,
            is_new=False,
            timed_out=False,
        )
    )
    manager.update_response_id = MagicMock()
    manager.set_ai_inactive = MagicMock()
    manager.db = MagicMock()
    return manager


@pytest.fixture
def sample_webhook_payload():
    """Valid WhatsApp text message webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "ENTRY_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "123456789"},
                            "messages": [
                                {
                                    "from": "34612345678",
                                    "id": "wamid.test123",
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {
                                        "body": "Busco un ático en la costa"
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
