"""Gmail inbox ingestion for morning audit."""

from __future__ import annotations

import email
import imaplib
import logging
import os
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, parseaddr

logger = logging.getLogger(__name__)


def _safe_date_ddmm(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%d-%m")
    try:
        return parsedate_to_datetime(value).strftime("%d-%m")
    except (TypeError, ValueError):
        return datetime.now().strftime("%d-%m")


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_snippet(message_obj: email.message.Message, max_len: int = 180) -> str:
    if message_obj.is_multipart():
        for part in message_obj.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", "")).lower()
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                    return " ".join(text.split())[:max_len]
    else:
        payload = message_obj.get_payload(decode=True)
        if payload:
            text = payload.decode(message_obj.get_content_charset() or "utf-8", errors="ignore")
            return " ".join(text.split())[:max_len]
    return ""


def fetch_gmail_messages(max_results: int = 20) -> list[dict[str, str]]:
    """
    Fetch inbox records via Gmail IMAP.

    Requires SMTP_EMAIL + SMTP_PASSWORD (app password for Gmail).
    Returns normalized records with keys:
    cliente, origen, telefono, direccion, consulta, fecha.
    """
    username = os.getenv("SMTP_EMAIL", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    imap_server = os.getenv("GMAIL_IMAP_SERVER", "imap.gmail.com").strip()
    query_filter = os.getenv("GMAIL_QUERY_FILTER", "").strip()

    if not username or not password:
        logger.info("ℹ️ Gmail credentials not configured; skipping IMAP fetch.")
        return []

    records: list[dict[str, str]] = []
    mail = imaplib.IMAP4_SSL(imap_server)
    try:
        mail.login(username, password)
        mail.select("inbox")

        if query_filter:
            status, msg_ids = mail.uid("search", None, f'X-GM-RAW "{query_filter}"')
            if status != "OK":
                logger.warning("⚠️ Gmail X-GM-RAW query failed; falling back to UNSEEN.")
                status, msg_ids = mail.uid("search", None, "UNSEEN")
        else:
            status, msg_ids = mail.uid("search", None, "UNSEEN")

        if status != "OK":
            logger.error("❌ Gmail search failed with status: %s", status)
            return []

        selected_ids = msg_ids[0].split()[-max_results:]
        for uid in selected_ids:
            fetch_status, data = mail.uid("fetch", uid, "(RFC822)")
            if fetch_status != "OK" or not data or not data[0]:
                continue

            raw_message = data[0][1]
            message_obj = email.message_from_bytes(raw_message)

            from_name, from_addr = parseaddr(_decode_header_value(message_obj.get("From")))
            subject = _decode_header_value(message_obj.get("Subject"))
            snippet = _extract_snippet(message_obj)
            consulta = subject or snippet or "Consulta por email"
            cliente = from_name or from_addr or "Cliente Email"

            records.append(
                {
                    "cliente": cliente,
                    "origen": "EM",
                    "telefono": "",
                    "direccion": "",
                    "consulta": consulta,
                    "fecha": _safe_date_ddmm(message_obj.get("Date")),
                }
            )
    except imaplib.IMAP4.error as exc:
        logger.error("❌ Gmail IMAP authentication/query failed: %s", exc)
    except Exception as exc:  # pragma: no cover
        logger.error("❌ Gmail fetch failed: %s", exc)
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    logger.info("✅ Gmail records fetched: %s", len(records))
    return records
