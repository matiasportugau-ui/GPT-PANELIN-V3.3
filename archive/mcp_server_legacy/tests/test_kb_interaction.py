"""Test enhanced KB modification capabilities for verbal interaction.

Tests new handlers:
- list_corrections: Retrieve corrections with filtering and pagination
- update_correction_status: Update correction status with password
- batch_validate_corrections: Validate multiple corrections at once
- Enhanced report_error: With better error handling
"""

import pytest

from mcp.handlers.governance import (
    handle_list_corrections,
    handle_update_correction_status,
    handle_batch_validate_corrections,
)
from mcp.handlers.errors import handle_report_error


class TestListCorrections:
    """Test list_corrections handler."""

    @pytest.mark.asyncio
    async def test_list_all_corrections(self):
        """List all corrections without filters."""
        result = await handle_list_corrections({})
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "corrections" in result
        assert "pagination" in result
        assert isinstance(result["corrections"], list)

    @pytest.mark.asyncio
    async def test_filter_by_status(self):
        """Filter corrections by status."""
        result = await handle_list_corrections({"status": "pending"})
        assert result["ok"] is True
        assert all(c.get("status") == "pending" for c in result["corrections"])

    @pytest.mark.asyncio
    async def test_pagination(self):
        """Test pagination parameters."""
        result = await handle_list_corrections({"limit": 5, "offset": 0})
        assert result["ok"] is True
        pagination = result["pagination"]
        assert pagination["limit"] == 5
        assert pagination["offset"] == 0
        assert "total" in pagination
        assert "has_more" in pagination

    @pytest.mark.asyncio
    async def test_invalid_limit(self):
        """Invalid limit returns error."""
        result = await handle_list_corrections({"limit": 1000})
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_LIMIT"

    @pytest.mark.asyncio
    async def test_invalid_offset(self):
        """Invalid offset returns error."""
        result = await handle_list_corrections({"offset": -1})
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_OFFSET"


class TestUpdateCorrectionStatus:
    """Test update_correction_status handler."""

    @pytest.mark.asyncio
    async def test_missing_password(self):
        """Missing password returns error."""
        result = await handle_update_correction_status({
            "correction_id": "COR-001",
            "new_status": "applied",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "PASSWORD_REQUIRED"

    @pytest.mark.asyncio
    async def test_invalid_password(self):
        """Invalid password returns error."""
        result = await handle_update_correction_status({
            "correction_id": "COR-001",
            "new_status": "applied",
            "password": "wrong",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_invalid_status(self):
        """Invalid status value returns error."""
        result = await handle_update_correction_status({
            "correction_id": "COR-001",
            "new_status": "invalid",
            "password": "mywolfy",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_STATUS"

    @pytest.mark.asyncio
    async def test_correction_not_found(self):
        """Non-existent correction returns error."""
        result = await handle_update_correction_status({
            "correction_id": "COR-999999",
            "new_status": "applied",
            "password": "mywolfy",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "CORRECTION_NOT_FOUND"


class TestBatchValidateCorrections:
    """Test batch_validate_corrections handler."""

    @pytest.mark.asyncio
    async def test_empty_batch(self):
        """Empty corrections array returns error."""
        result = await handle_batch_validate_corrections({"corrections": []})
        assert result["ok"] is False
        assert result["error"]["code"] == "EMPTY_BATCH"

    @pytest.mark.asyncio
    async def test_batch_too_large(self):
        """Batch with > 20 corrections returns error."""
        corrections = [
            {
                "kb_file": "bromyros_pricing_master.json",
                "field": f"test_field_{i}",
                "proposed_value": "test",
            }
            for i in range(21)
        ]
        result = await handle_batch_validate_corrections({"corrections": corrections})
        assert result["ok"] is False
        assert result["error"]["code"] == "BATCH_TOO_LARGE"

    @pytest.mark.asyncio
    async def test_successful_batch_validation(self):
        """Valid batch returns results for each correction."""
        corrections = [
            {
                "kb_file": "bromyros_pricing_master.json",
                "field": "meta.generated_from",
                "proposed_value": "test1.json",
            },
            {
                "kb_file": "accessories_catalog.json",
                "field": "version",
                "proposed_value": "2.0",
            },
        ]
        result = await handle_batch_validate_corrections({"corrections": corrections})
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "results" in result
        assert "summary" in result
        assert len(result["results"]) == 2
        
        # Check summary structure
        summary = result["summary"]
        assert "total_corrections" in summary
        assert "successful_validations" in summary
        assert "failed_validations" in summary
        assert summary["total_corrections"] == 2

    @pytest.mark.asyncio
    async def test_batch_includes_indices(self):
        """Batch results include batch_index for identification."""
        corrections = [
            {
                "kb_file": "bromyros_pricing_master.json",
                "field": "meta.generated_from",
                "proposed_value": "test.json",
            },
        ]
        result = await handle_batch_validate_corrections({"corrections": corrections})
        assert result["ok"] is True
        assert result["results"][0]["batch_index"] == 0
        assert "correction_input" in result["results"][0]


class TestEnhancedReportError:
    """Test enhanced report_error handler with v1 contract."""

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Missing required fields returns proper error."""
        result = await handle_report_error({
            "kb_file": "accessories_catalog.json",
            # Missing other required fields
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "MISSING_REQUIRED_FIELDS"
        assert "missing_fields" in result["error"]["details"]

    @pytest.mark.asyncio
    async def test_invalid_kb_file(self):
        """Invalid kb_file returns proper error."""
        result = await handle_report_error({
            "kb_file": "invalid_file.json",
            "field": "test",
            "wrong_value": "1",
            "correct_value": "2",
            "source": "user_correction",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_KB_FILE"
        assert "allowed" in result["error"]["details"]

    @pytest.mark.asyncio
    async def test_successful_error_report(self):
        """Successful error report returns v1 envelope."""
        result = await handle_report_error({
            "kb_file": "accessories_catalog.json",
            "field": "test_field",
            "wrong_value": "10.0",
            "correct_value": "15.0",
            "source": "conversation",
            "notes": "Detected error during verbal interaction",
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "correction" in result
        assert "total_pending" in result
        correction = result["correction"]
        assert correction["kb_file"] == "accessories_catalog.json"
        assert correction["source"] == "conversation"
        assert "id" in correction

    @pytest.mark.asyncio
    async def test_conversation_source_allowed(self):
        """'conversation' is a valid source value."""
        result = await handle_report_error({
            "kb_file": "accessories_catalog.json",
            "field": "test",
            "wrong_value": "1",
            "correct_value": "2",
            "source": "conversation",
        })
        assert result["ok"] is True
        assert result["correction"]["source"] == "conversation"

    @pytest.mark.asyncio
    async def test_legacy_format_backward_compatible(self):
        """Legacy format still supported for backward compatibility."""
        result = await handle_report_error(
            {
                "kb_file": "accessories_catalog.json",
                "field": "test",
                "wrong_value": "1",
                "correct_value": "2",
                "source": "user_correction",
            },
            legacy_format=True,
        )
        assert "message" in result
        assert "correction" in result
        # Legacy format doesn't have 'ok' or 'contract_version'
        assert "ok" not in result
