#!/usr/bin/env python3
"""
PANELIN Morning Audit - Phase 1
Monitors customer touchpoints and generates a daily summary.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
TARGET_WORKSHEET = "Daily Audit"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class PanelinAudit:
    """Main morning audit coordinator."""

    def __init__(self) -> None:
        self.results: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channels": {},
            "summary": {},
        }
        self.sheet = self._connect_sheets()

    def _connect_sheets(self) -> Any | None:
        """Connect to Google Sheets if configuration is present."""
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "").strip()
        sheet_id = os.getenv("GOOGLE_SHEETS_ID", "").strip()

        if not creds_path:
            logger.warning(
                "⚠️ Google Sheets credentials path missing. "
                "Set GOOGLE_SHEETS_CREDENTIALS_PATH."
            )
            return None

        if not sheet_id:
            logger.warning(
                "⚠️ Google Sheets ID missing. "
                "Set GOOGLE_SHEETS_ID to enable audit writes to Sheets."
            )
            return None

        creds_file = Path(creds_path)
        if not creds_file.exists():
            logger.warning("⚠️ Google credentials file not found: %s", creds_file)
            return None

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            logger.error(
                "❌ Missing dependencies. Install with: pip install -r requirements.txt"
            )
            return None

        try:
            creds = Credentials.from_service_account_file(
                str(creds_file),
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            gc = gspread.authorize(creds)
            sheet = gc.open_by_key(sheet_id)
            logger.info("✅ Connected to Google Sheets: %s", sheet.title)
            return sheet
        except Exception as exc:  # pragma: no cover (network/remote dependency)
            logger.error("❌ Google Sheets connection failed: %s", exc)
            return None

    def _audit_whatsapp(self) -> dict[str, Any]:
        """Phase 1 manual WhatsApp check placeholder."""
        logger.info("📱 Checking WhatsApp Web...")
        logger.warning(
            "⚠️  Phase 1 manual step: open WhatsApp Web and count unread messages."
        )
        return {
            "platform": "WhatsApp",
            "status": "manual_check_required",
            "message": "Count unread messages in WhatsApp Web.",
            "count": 0,
        }

    def _audit_facebook(self) -> dict[str, Any]:
        """Phase 1 manual Facebook check placeholder."""
        logger.info("📘 Checking Facebook Page...")
        logger.warning(
            "⚠️  Phase 1 manual step: check Facebook Page inbox and unread messages."
        )
        return {
            "platform": "Facebook",
            "status": "manual_check_required",
            "message": "Check Facebook Page inbox and unread messages.",
            "count": 0,
        }

    def _audit_mercadolibre(self) -> dict[str, Any]:
        """Phase 1 manual MercadoLibre check placeholder."""
        logger.info("🛍️ Checking MercadoLibre...")
        logger.warning(
            "⚠️  Phase 1 manual step: review MercadoLibre questions, messages, and orders."
        )
        return {
            "platform": "MercadoLibre",
            "status": "manual_check_required",
            "message": "Check MercadoLibre questions, messages, and new orders.",
            "count": 0,
        }

    def _audit_email(self) -> dict[str, Any]:
        """Phase 1 manual email check placeholder."""
        logger.info("📧 Checking Email...")
        logger.warning(
            "⚠️  Phase 1 manual step: review Gmail inbox and spam for customer inquiries."
        )
        return {
            "platform": "Email",
            "status": "manual_check_required",
            "message": "Check Gmail inbox and spam for customer inquiries.",
            "count": 0,
        }

    def run_audit(self) -> dict[str, Any] | None:
        """Run all channel audits."""
        try:
            logger.info("🔄 Running all channel audits...")
            self.results["channels"]["whatsapp"] = self._audit_whatsapp()
            self.results["channels"]["facebook"] = self._audit_facebook()
            self.results["channels"]["mercadolibre"] = self._audit_mercadolibre()
            self.results["channels"]["email"] = self._audit_email()
            logger.info("✅ All channel audits completed")
            return self.results
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Audit failed: %s", exc)
            return None

    def write_to_sheets(self) -> None:
        """Write rows to 'Daily Audit' worksheet (columns A-H) if configured."""
        if not self.sheet:
            logger.warning("⚠️ Skipping Google Sheets write (no sheet connection).")
            return

        try:
            ws = self.sheet.worksheet(TARGET_WORKSHEET)
        except Exception as exc:
            # gspread is an optional dependency; import lazily since self.sheet
            # being non-None guarantees a prior successful import.
            import gspread
            if not isinstance(exc, gspread.exceptions.WorksheetNotFound):
                logger.error(
                    "❌ Unexpected error accessing worksheet '%s': %s",
                    TARGET_WORKSHEET,
                    exc,
                )
                raise
            ws = self.sheet.add_worksheet(TARGET_WORKSHEET, rows=1000, cols=8)

        try:
            all_rows = ws.get_all_values()
            existing_keys: set[tuple[str, str, str]] = set()
            last_data_row = 0

            for row_number, row in enumerate(all_rows, start=1):
                normalized_row = (row + [""] * 8)[:8]
                if any(cell.strip() for cell in normalized_row):
                    last_data_row = row_number

                fecha = normalized_row[2].strip()
                cliente = normalized_row[3].strip()
                origen = normalized_row[4].strip().upper()
                if fecha and cliente and origen:
                    existing_keys.add((cliente.casefold(), fecha, origen))

            origin_by_channel = {
                "whatsapp": "WA",
                "facebook": "FB",
                "mercadolibre": "ML",
                "email": "EM",
            }
            fecha_hoy = datetime.now(timezone.utc).strftime("%d-%m")
            rows_to_insert: list[list[str]] = []
            pending_keys: set[tuple[str, str, str]] = set()

            for channel_key, data in self.results["channels"].items():
                origen = origin_by_channel.get(channel_key, "CL")
                cliente = f"Audit {data['platform']}"
                consulta = data.get("message", "")
                duplicate_key = (cliente.casefold(), fecha_hoy, origen)

                if duplicate_key in existing_keys or duplicate_key in pending_keys:
                    logger.info(
                        "ℹ️ Skipping duplicate row for cliente=%s fecha=%s origen=%s",
                        cliente,
                        fecha_hoy,
                        origen,
                    )
                    continue

                rows_to_insert.append(
                    [
                        "",  # A: Asig.
                        "Pendiente",  # B: Estado
                        fecha_hoy,  # C: Fecha
                        cliente,  # D: Cliente
                        origen,  # E: Orig.
                        "",  # F: Telefono-Contacto
                        "",  # G: Direccion/Zona
                        consulta,  # H: Consulta
                    ]
                )
                pending_keys.add(duplicate_key)

            if not rows_to_insert:
                logger.info("ℹ️ No new rows to insert (all duplicates already exist).")
                return

            start_row = last_data_row + 1 if last_data_row > 0 else 1
            end_row = start_row + len(rows_to_insert) - 1
            ws.update(f"A{start_row}:H{end_row}", rows_to_insert)
            logger.info(
                "✅ Inserted %s row(s) into worksheet '%s' (A%s:H%s)",
                len(rows_to_insert),
                TARGET_WORKSHEET,
                start_row,
                end_row,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Failed to write to Google Sheets: %s", exc)

    def send_summary_email(self) -> None:
        """Phase 2 placeholder for daily summary email delivery."""
        logger.info("📬 Email summary placeholder (Phase 2)")


def main() -> int:
    """Program entry point."""
    logger.info("=" * 60)
    logger.info("🌅 PANELIN MORNING AUDIT STARTED")
    logger.info("=" * 60)

    load_dotenv()
    audit = PanelinAudit()
    results = audit.run_audit()

    if not results:
        logger.error("❌ Morning audit did not complete.")
        return 1

    audit.write_to_sheets()
    audit.send_summary_email()

    logger.info("=" * 60)
    logger.info("🎉 MORNING AUDIT COMPLETE")
    logger.info("📝 Logs saved to: %s", LOG_FILE)
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
