"""Tests for allowlist validation logic."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from panelin_sheets_orchestrator.service import validate_write_ranges


class TestValidateWriteRanges:
    def test_all_allowed(self):
        writes = [
            {"range": "Sheet1!A1", "values": [["v"]]},
            {"range": "Sheet1!B2", "values": [["v"]]},
        ]
        allowlist = ["Sheet1!A1", "Sheet1!B2", "Sheet1!C3"]
        validate_write_ranges(writes, allowlist)

    def test_disallowed_range_raises(self):
        writes = [
            {"range": "Sheet1!A1", "values": [["v"]]},
            {"range": "Sheet1!Z99", "values": [["hacked"]]},
        ]
        allowlist = ["Sheet1!A1"]
        with pytest.raises(HTTPException) as exc_info:
            validate_write_ranges(writes, allowlist)
        assert exc_info.value.status_code == 400
        assert "Sheet1!Z99" in str(exc_info.value.detail)

    def test_empty_writes_pass(self):
        validate_write_ranges([], ["Sheet1!A1"])

    def test_empty_allowlist_rejects(self):
        writes = [{"range": "Sheet1!A1", "values": [["v"]]}]
        with pytest.raises(HTTPException):
            validate_write_ranges(writes, [])

    def test_none_range_rejected(self):
        writes = [{"values": [["v"]]}]
        with pytest.raises(HTTPException):
            validate_write_ranges(writes, ["Sheet1!A1"])
