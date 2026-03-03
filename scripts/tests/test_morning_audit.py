"""Tests for scripts/morning_audit.py.

How to run:
    pytest scripts/tests/test_morning_audit.py -v

This test suite validates:
1. PanelinAudit initialises without Google Sheets credentials
2. Individual channel audit methods return expected structure
3. run_audit() aggregates all channel results correctly
4. write_to_sheets() skips gracefully when no sheet is connected
5. send_summary_email() is a safe Phase-2 placeholder
6. main() entry-point returns 0 on success
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging

import pytest

# Ensure the repo root is on the path so the scripts package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.morning_audit import PanelinAudit, main  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def audit_no_sheets():
    """Return a PanelinAudit instance with Google Sheets disabled."""
    with patch.dict("os.environ", {"GOOGLE_SHEETS_ID": "", "GOOGLE_SHEETS_CREDENTIALS_PATH": ""}):
        instance = PanelinAudit()
    assert instance.sheet is None
    return instance


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestPanelinAuditInit:
    """PanelinAudit.__init__ / _connect_sheets."""

    def test_no_sheets_credentials_returns_none(self):
        """When GOOGLE_SHEETS_ID is empty the sheet attribute must be None."""
        with patch.dict("os.environ", {"GOOGLE_SHEETS_ID": "", "GOOGLE_SHEETS_CREDENTIALS_PATH": ""}):
            audit = PanelinAudit()
        assert audit.sheet is None

    def test_results_initial_structure(self, audit_no_sheets):
        """results dict contains the expected top-level keys on creation."""
        audit = audit_no_sheets
        assert "timestamp" in audit.results
        assert "channels" in audit.results
        assert "summary" in audit.results
        assert audit.results["channels"] == {}

    def test_missing_creds_file_returns_none(self, tmp_path):
        """When credentials file path points to a missing file, sheet is None."""
        fake_path = str(tmp_path / "nonexistent.json")
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_SHEETS_ID": "fake_id",
                "GOOGLE_SHEETS_CREDENTIALS_PATH": fake_path,
            },
        ):
            audit = PanelinAudit()
        assert audit.sheet is None


# ---------------------------------------------------------------------------
# Individual channel audits
# ---------------------------------------------------------------------------


class TestChannelAudits:
    """Individual _audit_* methods return the expected payload structure."""

    def test_audit_whatsapp_structure(self, audit_no_sheets):
        result = audit_no_sheets._audit_whatsapp()
        assert result["platform"] == "WhatsApp"
        assert result["status"] == "manual_check_required"
        assert "message" in result
        assert "count" in result

    def test_audit_facebook_structure(self, audit_no_sheets):
        result = audit_no_sheets._audit_facebook()
        assert result["platform"] == "Facebook"
        assert result["status"] == "manual_check_required"
        assert "message" in result
        assert "count" in result

    def test_audit_mercadolibre_structure(self, audit_no_sheets):
        result = audit_no_sheets._audit_mercadolibre()
        assert result["platform"] == "MercadoLibre"
        assert result["status"] == "manual_check_required"
        assert "message" in result
        assert "count" in result

    def test_audit_email_structure(self, audit_no_sheets):
        result = audit_no_sheets._audit_email()
        assert result["platform"] == "Email"
        assert result["status"] == "manual_check_required"
        assert "message" in result
        assert "count" in result


# ---------------------------------------------------------------------------
# run_audit
# ---------------------------------------------------------------------------


class TestRunAudit:
    """run_audit() aggregates results from all four channels."""

    def test_run_audit_returns_dict(self, audit_no_sheets):
        results = audit_no_sheets.run_audit()
        assert isinstance(results, dict)

    def test_run_audit_contains_all_channels(self, audit_no_sheets):
        results = audit_no_sheets.run_audit()
        assert set(results["channels"].keys()) == {
            "whatsapp",
            "facebook",
            "mercadolibre",
            "email",
        }

    def test_run_audit_populates_instance_results(self, audit_no_sheets):
        results = audit_no_sheets.run_audit()
        assert results is audit_no_sheets.results
        assert audit_no_sheets.results["channels"]["whatsapp"]["platform"] == "WhatsApp"

    def test_run_audit_timestamp_present(self, audit_no_sheets):
        results = audit_no_sheets.run_audit()
        assert results["timestamp"]  # non-empty string


# ---------------------------------------------------------------------------
# write_to_sheets
# ---------------------------------------------------------------------------


class TestWriteToSheets:
    """write_to_sheets() behaves correctly when no sheet is configured."""

    def test_skips_gracefully_without_sheet(self, audit_no_sheets, caplog):
        """write_to_sheets should log a warning and return without raising."""
        audit_no_sheets.run_audit()
        with caplog.at_level(logging.WARNING):
            audit_no_sheets.write_to_sheets()
        assert any("Skipping" in r.message for r in caplog.records)

    def test_writes_when_sheet_is_available(self, audit_no_sheets):
        """write_to_sheets should call ws.update when a sheet mock is provided."""
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = []
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws

        audit_no_sheets.sheet = mock_sheet
        audit_no_sheets.run_audit()
        audit_no_sheets.write_to_sheets()

        mock_ws.update.assert_called_once()
        call_args = mock_ws.update.call_args
        # First arg is the range string, second is the rows list
        range_str, rows = call_args[0]
        assert range_str.startswith("A")
        assert len(rows) == 4  # one row per channel

    def test_skips_duplicate_rows(self, audit_no_sheets):
        """write_to_sheets should not insert rows that already exist in the sheet."""
        from datetime import datetime

        fecha_hoy = datetime.now().strftime("%d-%m")
        existing = [
            ["", "Pendiente", fecha_hoy, "Audit WhatsApp", "WA", "", "", "Count unread messages in WhatsApp Web."],
            ["", "Pendiente", fecha_hoy, "Audit Facebook", "FB", "", "", "Check Facebook Page inbox and unread messages."],
            ["", "Pendiente", fecha_hoy, "Audit MercadoLibre", "ML", "", "", "Check MercadoLibre questions, messages, and new orders."],
            ["", "Pendiente", fecha_hoy, "Audit Email", "EM", "", "", "Check Gmail inbox and spam for customer inquiries."],
        ]
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = existing
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws

        audit_no_sheets.sheet = mock_sheet
        audit_no_sheets.run_audit()
        audit_no_sheets.write_to_sheets()

        mock_ws.update.assert_not_called()


# ---------------------------------------------------------------------------
# send_summary_email
# ---------------------------------------------------------------------------


class TestSendSummaryEmail:
    """send_summary_email() is a Phase-2 placeholder and must not raise."""

    def test_does_not_raise(self, audit_no_sheets):
        audit_no_sheets.send_summary_email()  # should complete without error


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------


class TestMain:
    """main() integration test using mocked PanelinAudit."""

    def test_main_returns_zero_on_success(self):
        """main() must return 0 when the audit completes successfully."""
        with (
            patch.dict("os.environ", {"GOOGLE_SHEETS_ID": "", "GOOGLE_SHEETS_CREDENTIALS_PATH": ""}),
            patch("scripts.morning_audit.load_dotenv"),
        ):
            exit_code = main()
        assert exit_code == 0
