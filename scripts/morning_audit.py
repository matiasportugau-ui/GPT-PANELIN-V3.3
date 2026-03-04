#!/usr/bin/env python3
"""PANELIN Morning Audit automation for Atead worksheet."""

from __future__ import annotations

import logging
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
DEFAULT_SHEETS_ID = "1RHJ1eQlCWMcWY5NKkHCsH5F5XavC9yebh97bruJilbs"
TARGET_WORKSHEET = "Atead"
VALID_ORIGINS = {"WA", "ML", "CL", "IG", "EM"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def normalize_text(value: str) -> str:
    """Normalize text for duplicate checks."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.casefold().split())


def normalize_date_ddmm(value: str | None) -> str:
    """Normalize date to DD-MM or fallback to today's date."""
    if not value:
        return datetime.now().strftime("%d-%m")
    for fmt in ("%d-%m", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%d-%m")
        except ValueError:
            continue
    return datetime.now().strftime("%d-%m")


def build_duplicate_key(cliente: str, fecha: str, origen: str) -> tuple[str, str, str]:
    """Build normalized duplicate key using Cliente + Fecha + Orig."""
    return (
        normalize_text(cliente),
        normalize_date_ddmm(fecha),
        (origen or "CL").strip().upper(),
    )


def build_sheet_row(record: dict[str, str]) -> list[str]:
    """Map normalized record to Atead worksheet columns A-H."""
    origen = (record.get("origen", "CL").strip().upper() or "CL")
    if origen not in VALID_ORIGINS:
        origen = "CL"
    return [
        "",  # A Asig.
        "Pendiente",  # B Estado
        normalize_date_ddmm(record.get("fecha")),
        record.get("cliente", "").strip() or "Cliente",
        origen,
        record.get("telefono", "").strip(),
        record.get("direccion", "").strip(),
        record.get("consulta", "").strip() or "Consulta pendiente",
    ]


class PanelinAudit:
    """Main morning audit coordinator."""

    def __init__(self) -> None:
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "channels": {},
            "summary": {},
        }
        self.sheet = self._connect_sheets()

    def _connect_sheets(self) -> Any | None:
        """Connect to Google Sheets if configuration is present."""
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "").strip()
        sheet_id = os.getenv("GOOGLE_SHEETS_ID", DEFAULT_SHEETS_ID).strip()
        if not creds_path:
            logger.warning(
                "⚠️ Google Sheets credentials path missing. "
                "Set GOOGLE_SHEETS_CREDENTIALS_PATH."
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
        """Collect WhatsApp records from API with manual fallback."""
        logger.info("📱 Checking WhatsApp...")
        try:
            from fetch_whatsapp import fetch_whatsapp_messages
        except ImportError as exc:
            logger.error("❌ Could not import WhatsApp fetcher: %s", exc)
            return {"platform": "WhatsApp", "status": "error", "message": str(exc), "records": []}

        records = fetch_whatsapp_messages()
        if records:
            return {
                "platform": "WhatsApp",
                "status": "ok",
                "message": f"WhatsApp records fetched: {len(records)}",
                "records": records,
            }

        sample_cliente = os.getenv("WA_FALLBACK_CLIENTE", "Audit WhatsApp")
        sample_consulta = os.getenv(
            "WA_FALLBACK_CONSULTA",
            "Revisar mensajes no leídos en WhatsApp Business.",
        )
        return {
            "platform": "WhatsApp",
            "status": "manual_fallback",
            "message": "WhatsApp API no configurada; usando registro manual de respaldo.",
            "records": [
                {
                    "cliente": sample_cliente,
                    "origen": "WA",
                    "telefono": "",
                    "direccion": "",
                    "consulta": sample_consulta,
                    "fecha": datetime.now().strftime("%d-%m"),
                }
            ],
        }

    def _audit_facebook(self) -> dict[str, Any]:
        """Collect Meta (FB/IG) records via API with graceful fallback."""
        logger.info("📘 Checking Meta conversations...")
        try:
            from fetch_meta import fetch_meta_messages
        except ImportError as exc:
            logger.error("❌ Could not import Meta fetcher: %s", exc)
            return {"platform": "Meta", "status": "error", "message": str(exc), "records": []}

        records = fetch_meta_messages()
        status = "ok" if records else "no_records"
        return {
            "platform": "Meta",
            "status": status,
            "message": f"Meta records fetched: {len(records)}",
            "records": records,
        }

    def _audit_mercadolibre(self) -> dict[str, Any]:
        """Collect MercadoLibre unread records via API."""
        logger.info("🛍️ Checking MercadoLibre...")
        try:
            from fetch_mercadolibre import fetch_mercadolibre_messages
        except ImportError as exc:
            logger.error("❌ Could not import MercadoLibre fetcher: %s", exc)
            return {"platform": "MercadoLibre", "status": "error", "message": str(exc), "records": []}

        records = fetch_mercadolibre_messages()
        status = "ok" if records else "no_records"
        return {
            "platform": "MercadoLibre",
            "status": status,
            "message": f"MercadoLibre records fetched: {len(records)}",
            "records": records,
        }

    def _audit_email(self) -> dict[str, Any]:
        """Collect Gmail records using IMAP and query filter."""
        logger.info("📧 Checking Gmail...")
        try:
            from fetch_gmail import fetch_gmail_messages
        except ImportError as exc:
            logger.error("❌ Could not import Gmail fetcher: %s", exc)
            return {"platform": "Email", "status": "error", "message": str(exc), "records": []}

        records = fetch_gmail_messages()
        status = "ok" if records else "no_records"
        return {
            "platform": "Email",
            "status": status,
            "message": f"Gmail records fetched: {len(records)}",
            "records": records,
        }

    def run_audit(self) -> dict[str, Any] | None:
        """Run all channel audits."""
        try:
            logger.info("🔄 Running all channel audits...")
            self.results["channels"]["whatsapp"] = self._audit_whatsapp()
            self.results["channels"]["facebook"] = self._audit_facebook()
            self.results["channels"]["mercadolibre"] = self._audit_mercadolibre()
            self.results["channels"]["email"] = self._audit_email()
            total_records = sum(
                len(channel_data.get("records", []))
                for channel_data in self.results["channels"].values()
            )
            self.results["summary"]["total_records"] = total_records
            logger.info("📊 Total records collected: %s", total_records)
            logger.info("✅ All channel audits completed")
            return self.results
        except Exception as exc:  # pragma: no cover
            logger.error("❌ Audit failed: %s", exc)
            return None

    def write_to_sheets(self) -> None:
        """Write rows to Atead worksheet (columns A-H) with dedupe guard."""
        if not self.sheet:
            logger.warning("⚠️ Skipping Google Sheets write (no sheet connection).")
            return

        try:
            ws = self.sheet.worksheet(TARGET_WORKSHEET)
        except Exception:
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
                    existing_keys.add(build_duplicate_key(cliente, fecha, origen))

            rows_to_insert: list[list[str]] = []
            pending_keys: set[tuple[str, str, str]] = set()

            for channel_data in self.results["channels"].values():
                for record in channel_data.get("records", []):
                    duplicate_key = build_duplicate_key(
                        record.get("cliente", ""),
                        record.get("fecha", ""),
                        record.get("origen", "CL"),
                    )

                    if duplicate_key in existing_keys or duplicate_key in pending_keys:
                        logger.info(
                            "ℹ️ Skipping duplicate row for cliente=%s fecha=%s origen=%s",
                            record.get("cliente", ""),
                            normalize_date_ddmm(record.get("fecha", "")),
                            record.get("origen", "CL"),
                        )
                        continue

                    rows_to_insert.append(build_sheet_row(record))
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
        """Summary log hook for optional notification integrations."""
        logger.info(
            "📬 Summary: %s record(s) prepared",
            self.results.get("summary", {}).get("total_records", 0),
        )


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
