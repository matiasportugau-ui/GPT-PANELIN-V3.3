"""drive_uploader.py — Upload PDFs to Google Drive and return shareable URL."""
from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger("panelin.drive")

_drive_service = None


def _get_drive_service():
    """Lazy-initialize Google Drive service."""
    global _drive_service
    if _drive_service is None:
        try:
            from google.auth import default as gauth_default
            from googleapiclient.discovery import build
            creds, _ = gauth_default(scopes=["https://www.googleapis.com/auth/drive"])
            _drive_service = build("drive", "v3", credentials=creds)
        except Exception as exc:
            logger.warning("Google Drive service unavailable: %s", exc)
            return None
    return _drive_service


def generate_doc_number(prefix: str = "BMC") -> str:
    """Generate a unique document number: PREFIX-YYYYMMDD-XXXXXX."""
    now = datetime.now()
    suffix = hashlib.md5(str(now.timestamp()).encode()).hexdigest()[:6].upper()
    return f"{prefix}-{now.strftime('%Y%m%d')}-{suffix}"


def sanitize_filename(name: str) -> str:
    """Sanitize client name for use in a filename."""
    safe = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"\s+", "_", safe)[:40]


def ensure_folder_structure(year: int, month: int) -> Optional[str]:
    """Ensure year/month folder structure exists in Google Drive.

    Returns the folder ID or None if Drive is unavailable.
    """
    svc = _get_drive_service()
    if svc is None:
        return None

    root_folder = os.environ.get("DRIVE_ROOT_FOLDER_ID", "")
    if not root_folder:
        return None

    try:
        # Find or create year folder
        year_folder = _find_or_create_folder(svc, str(year), root_folder)
        # Find or create month folder inside year
        month_names = [
            "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        month_name = f"{month:02d}-{month_names[month]}"
        month_folder = _find_or_create_folder(svc, month_name, year_folder)
        return month_folder
    except Exception as exc:
        logger.warning("ensure_folder_structure error: %s", exc)
        return None


def _find_or_create_folder(svc, name: str, parent_id: str) -> str:
    """Find existing folder or create it, returning folder ID."""
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = svc.files().list(q=query, fields="files(id,name)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = svc.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_pdf(
    pdf_bytes: bytes,
    filename: str,
    folder_id: Optional[str] = None,
) -> tuple[str, str, str]:
    """Upload PDF bytes to Google Drive.

    Returns (file_id, view_url, download_url).
    Raises RuntimeError if Drive is unavailable.
    """
    svc = _get_drive_service()
    if svc is None:
        raise RuntimeError("Google Drive service not available")

    from googleapiclient.http import MediaIoBaseUpload
    import io

    meta: dict = {"name": filename, "mimeType": "application/pdf"}
    if folder_id:
        meta["parents"] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf")
    file_ = svc.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = file_["id"]

    # Make publicly viewable
    svc.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    view_url = f"https://drive.google.com/file/d/{file_id}/view"
    download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    return file_id, view_url, download_url


def get_drive_path(year: int, month: int, filename: str) -> str:
    """Return a human-readable path string for the uploaded file."""
    month_names = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    month_name = f"{month:02d}-{month_names[month]}"
    return f"Cotizaciones/{year}/{month_name}/{filename}"
