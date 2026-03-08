"""Test Wolf API KB Write handlers return v1 contract envelopes.

This test suite validates that the v3.4 Wolf API KB Write handlers:
1. Enforce password validation for write operations
2. Validate input parameters (phone format, required fields)
3. Return proper v1 contract envelope structures
4. Allow lookup_customer without password

These tests run in CI via .github/workflows/mcp-tests.yml
"""

import pytest
from unittest.mock import MagicMock

from panelin_mcp_server.handlers.wolf_kb_write import (
    handle_persist_conversation,
    handle_register_correction,
    handle_save_customer,
    handle_lookup_customer,
    configure_wolf_kb_client,
    KB_WRITE_PASSWORD,
)
from mcp_tools.contracts import (
    WOLF_KB_WRITE_ERROR_CODES,
    LOOKUP_CUSTOMER_ERROR_CODES,
)


def _make_mock_client(**overrides):
    """Create a mock Wolf API client with configurable responses."""
    client = MagicMock()
    client.persist_conversation.return_value = overrides.get(
        "persist_conversation",
        {"success": True, "data": {"conversation_id": "conv-test-001"}, "timestamp": "2026-02-14T00:00:00"},
    )
    client.register_correction.return_value = overrides.get(
        "register_correction",
        {"success": True, "data": {"correction_id": "cor-test-001"}, "timestamp": "2026-02-14T00:00:00"},
    )
    client.save_customer.return_value = overrides.get(
        "save_customer",
        {"success": True, "data": {"customer_id": "cust-test-001"}, "timestamp": "2026-02-14T00:00:00"},
    )
    client.lookup_customer.return_value = overrides.get(
        "lookup_customer",
        {"success": True, "data": {"customers": [{"name": "Test", "phone": "091234567"}]}, "timestamp": "2026-02-14T00:00:00"},
    )
    return client


@pytest.fixture(autouse=True)
def setup_mock_client():
    """Configure a mock Wolf client for all tests."""
    client = _make_mock_client()
    configure_wolf_kb_client(client)
    yield client
    configure_wolf_kb_client(None)


class TestPersistConversation:
    """Test persist_conversation handler."""

    @pytest.mark.asyncio
    async def test_missing_password_returns_error(self):
        result = await handle_persist_conversation({
            "client_id": "test-client",
            "summary": "Test summary",
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert result["error"]["code"] == "PASSWORD_REQUIRED"

    @pytest.mark.asyncio
    async def test_wrong_password_returns_error(self):
        result = await handle_persist_conversation({
            "client_id": "test-client",
            "summary": "Test summary",
            "password": "wrongpassword",
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert result["error"]["code"] == "INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        result = await handle_persist_conversation({
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_success_returns_v1_envelope(self):
        result = await handle_persist_conversation({
            "client_id": "test-client",
            "summary": "Cotización ISODEC 100mm",
            "quotation_ref": "QT-001",
            "products_discussed": ["ISODEC_EPS_100"],
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "conversation_id" in result
        assert "stored_at" in result

    @pytest.mark.asyncio
    async def test_wolf_api_failure(self, setup_mock_client):
        setup_mock_client.persist_conversation.return_value = {
            "success": False, "error": "Connection refused",
        }
        result = await handle_persist_conversation({
            "client_id": "test-client",
            "summary": "Test",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "WOLF_API_ERROR"


class TestRegisterCorrection:
    """Test register_correction handler."""

    @pytest.mark.asyncio
    async def test_missing_password_returns_error(self):
        result = await handle_register_correction({
            "source_file": "bromyros_pricing_master.json",
            "field_path": "products[0].price",
            "old_value": "100",
            "new_value": "105",
            "reason": "Price updated",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "PASSWORD_REQUIRED"

    @pytest.mark.asyncio
    async def test_wrong_password_returns_error(self):
        result = await handle_register_correction({
            "source_file": "test.json",
            "field_path": "x",
            "old_value": "a",
            "new_value": "b",
            "reason": "fix",
            "password": "badpass",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_success_returns_v1_envelope(self):
        result = await handle_register_correction({
            "source_file": "bromyros_pricing_master.json",
            "field_path": "products[0].price_usd",
            "old_value": "100.00",
            "new_value": "105.50",
            "reason": "Price correction per BMC update Feb 2026",
            "reported_by": "Mauro",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "correction_id" in result
        assert "stored_at" in result


class TestSaveCustomer:
    """Test save_customer handler."""

    @pytest.mark.asyncio
    async def test_missing_password_returns_error(self):
        result = await handle_save_customer({
            "name": "Juan Perez",
            "phone": "091234567",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "PASSWORD_REQUIRED"

    @pytest.mark.asyncio
    async def test_invalid_phone_format(self):
        result = await handle_save_customer({
            "name": "Juan Perez",
            "phone": "12345",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PHONE"

    @pytest.mark.asyncio
    async def test_valid_phone_09_format(self):
        result = await handle_save_customer({
            "name": "Juan Perez",
            "phone": "091234567",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "customer_id" in result

    @pytest.mark.asyncio
    async def test_valid_phone_598_format(self):
        result = await handle_save_customer({
            "name": "Maria Garcia",
            "phone": "+59891234567",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"

    @pytest.mark.asyncio
    async def test_phone_with_spaces_normalized(self):
        result = await handle_save_customer({
            "name": "Pedro Lopez",
            "phone": "091 234 567",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_success_with_all_fields(self):
        result = await handle_save_customer({
            "name": "Ana Martinez",
            "phone": "099876543",
            "address": "Av. Rivera 1234",
            "city": "Montevideo",
            "department": "Montevideo",
            "notes": "Proyecto galpón industrial",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert "stored_at" in result


class TestLookupCustomer:
    """Test lookup_customer handler — no password required."""

    @pytest.mark.asyncio
    async def test_no_password_needed(self):
        result = await handle_lookup_customer({
            "search_query": "Juan",
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"

    @pytest.mark.asyncio
    async def test_query_too_short(self):
        result = await handle_lookup_customer({
            "search_query": "J",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "QUERY_TOO_SHORT"

    @pytest.mark.asyncio
    async def test_success_returns_customers_and_count(self):
        result = await handle_lookup_customer({
            "search_query": "Test",
        })
        assert result["ok"] is True
        assert "customers" in result
        assert "count" in result
        assert isinstance(result["customers"], list)
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_wolf_api_failure(self, setup_mock_client):
        setup_mock_client.lookup_customer.return_value = {
            "success": False, "error": "Timeout",
        }
        result = await handle_lookup_customer({
            "search_query": "Test",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "WOLF_API_ERROR"


class TestErrorCodeRegistries:
    """Validate error codes are properly registered."""

    def test_wolf_kb_write_error_codes_complete(self):
        expected = {"PASSWORD_REQUIRED", "INVALID_PASSWORD", "INVALID_PHONE", "WOLF_API_ERROR", "INTERNAL_ERROR"}
        assert set(WOLF_KB_WRITE_ERROR_CODES.keys()) == expected

    def test_lookup_customer_error_codes_complete(self):
        expected = {"QUERY_TOO_SHORT", "WOLF_API_ERROR", "INTERNAL_ERROR"}
        assert set(LOOKUP_CUSTOMER_ERROR_CODES.keys()) == expected
