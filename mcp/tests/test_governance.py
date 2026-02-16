"""Test self-healing governance handlers return v1 contract envelopes.

Validates that validate_correction and commit_correction handlers:
1. Return proper v1 contract envelope structures
2. Validate KB file against whitelist
3. Detect value mismatches
4. Generate impact analysis reports
5. Handle the validate-then-commit flow correctly
6. Use proper error codes from contract registry
"""

import pytest

from mcp.handlers.governance import (
    handle_validate_correction,
    handle_commit_correction,
    _pending_changes,
    _pending_changes_lock,
)
from mcp_tools.contracts import (
    VALIDATE_CORRECTION_ERROR_CODES,
    COMMIT_CORRECTION_ERROR_CODES,
)


class TestValidateCorrection:
    """Test validate_correction handler returns v1 contract envelope."""

    @pytest.mark.asyncio
    async def test_success_response_structure(self):
        """Successful validation returns v1 envelope with analysis."""
        result = await handle_validate_correction({
            "kb_file": "bromyros_pricing_master.json",
            "field": "meta.generated_from",
            "proposed_value": "updated_source.json",
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert "validation" in result
        assert "impact_analysis" in result
        assert "change_report" in result
        assert "change_id" in result
        # Validate impact_analysis structure
        impact = result["impact_analysis"]
        assert "quotations_analyzed" in impact
        assert "quotations_affected" in impact
        assert "total_impact_usd" in impact
        assert "affected_quotations" in impact
        # Validate change_report structure
        report = result["change_report"]
        assert "change_id" in report
        assert "severity" in report
        assert "summary" in report
        assert report["severity"] in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_invalid_kb_file_error(self):
        """Invalid kb_file returns v1 error with INVALID_KB_FILE code."""
        result = await handle_validate_correction({
            "kb_file": "nonexistent_file.json",
            "field": "price",
            "proposed_value": "100",
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert result["error"]["code"] == VALIDATE_CORRECTION_ERROR_CODES["INVALID_KB_FILE"]

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        """Path traversal attempts are sanitized and rejected."""
        result = await handle_validate_correction({
            "kb_file": "../../etc/passwd",
            "field": "root",
            "proposed_value": "hacked",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == VALIDATE_CORRECTION_ERROR_CODES["INVALID_KB_FILE"]

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Missing required fields return v1 error."""
        result = await handle_validate_correction({
            "kb_file": "bromyros_pricing_master.json",
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert "error" in result
        assert result["error"]["code"] in VALIDATE_CORRECTION_ERROR_CODES

    @pytest.mark.asyncio
    async def test_value_mismatch_detection(self):
        """Detects when current_value doesn't match actual value."""
        result = await handle_validate_correction({
            "kb_file": "bromyros_pricing_master.json",
            "field": "meta.generated_from",
            "current_value": "WRONG_VALUE_THAT_DOES_NOT_EXIST",
            "proposed_value": "new_value",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == VALIDATE_CORRECTION_ERROR_CODES["VALUE_MISMATCH"]

    @pytest.mark.asyncio
    async def test_change_id_cached_for_commit(self):
        """Validated change is cached for subsequent commit."""
        result = await handle_validate_correction({
            "kb_file": "bromyros_pricing_master.json",
            "field": "meta.generated_from",
            "proposed_value": "test_source.json",
        })
        assert result["ok"] is True
        change_id = result["change_id"]
        with _pending_changes_lock:
            assert change_id in _pending_changes
            # Cleanup
            _pending_changes.pop(change_id, None)


class TestCommitCorrection:
    """Test commit_correction handler returns v1 contract envelope."""

    @pytest.mark.asyncio
    async def test_missing_change_id_error(self):
        """Missing change_id returns CHANGE_NOT_FOUND error."""
        result = await handle_commit_correction({
            "confirm": True,
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert result["error"]["code"] == COMMIT_CORRECTION_ERROR_CODES["CHANGE_NOT_FOUND"]

    @pytest.mark.asyncio
    async def test_confirmation_required(self):
        """Commit without confirm=true returns CONFIRMATION_REQUIRED."""
        result = await handle_commit_correction({
            "change_id": "CHG-DOES_NOT_EXIST",
            "confirm": False,
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert result["error"]["code"] == COMMIT_CORRECTION_ERROR_CODES["CONFIRMATION_REQUIRED"]

    @pytest.mark.asyncio
    async def test_unknown_change_id_error(self):
        """Unknown change_id returns CHANGE_NOT_FOUND error."""
        result = await handle_commit_correction({
            "change_id": "CHG-NONEXISTENT",
            "confirm": True,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == COMMIT_CORRECTION_ERROR_CODES["CHANGE_NOT_FOUND"]

    @pytest.mark.asyncio
    async def test_full_validate_then_commit_flow(self):
        """End-to-end: validate → commit flow works correctly."""
        # Step 1: Validate
        validate_result = await handle_validate_correction({
            "kb_file": "bromyros_pricing_master.json",
            "field": "meta.generated_from",
            "proposed_value": "e2e_test_value.json",
            "source": "validation_check",
            "notes": "E2E test",
        })
        assert validate_result["ok"] is True
        change_id = validate_result["change_id"]

        # Step 2: Commit
        commit_result = await handle_commit_correction({
            "change_id": change_id,
            "confirm": True,
        })
        assert commit_result["ok"] is True
        assert commit_result["contract_version"] == "v1"
        assert "correction" in commit_result
        assert commit_result["correction"]["kb_file"] == "bromyros_pricing_master.json"
        assert commit_result["correction"]["status"] == "pending"
        assert "impact_summary" in commit_result["correction"]
        assert "change_id" in commit_result["correction"]

        # Step 3: Same change_id should not be reusable
        retry_result = await handle_commit_correction({
            "change_id": change_id,
            "confirm": True,
        })
        assert retry_result["ok"] is False
        assert retry_result["error"]["code"] == COMMIT_CORRECTION_ERROR_CODES["CHANGE_NOT_FOUND"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
