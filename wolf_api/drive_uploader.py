"""
drive_uploader.py — Google Drive operations for Panelin PDF cotizaciones
"""

import os
import io
import re
import logging
from datetime import datetime
from typing import Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger("panelin.drive")

ROOT_FOLDER_NAME = "Cotizaciones Panelin"
SA_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/credentials/sa-key.json")

_drive_service = None
_root_folder_id = None

MESES = {
  1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
  5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
  9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def get_drive_service():
  """Get or create cached Google Drive API service."""
  global _drive_service
  if _drive_service:
    return _drive_service
    try:
      from google.auth import default
      credentials, _ = default(scopes=["https://www.googleapis.com/auth/drive"])
      _drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
      logger.info("Drive service initialized via default credentials")
    except Exception:
      try:
        credentials = service_account.Credentials.from_service_account_file(
          SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/drive"])
        _drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        logger.info(f"Drive service initialized via SA key: {SA_KEY_PATH}")
      except Exception as e:
        logger.error(f"Failed to initialize Drive service: {e}")
        raise RuntimeError(f"Cannot initialize Google Drive: {e}")
        return _drive_service


def _find_folder(name: str, parent_id: Optional[str] = None) -> Optional[str]:
  """Find a folder by name (optionally within a parent). Returns folder ID or None."""
  service = get_drive_service()
  query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
  if parent_id:
    query += f" and '{parent_id}' in parents"
    results = service.files().list(
    q=query, spaces="drive", fields="files(id, name)", pageSize=5
    ).execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def _create_folder(name: str, parent_id: Optional[str] = None) -> str:
  """Create a folder in Drive. Returns new folder ID."""
  service = get_drive_service()
  metadata = {
  "name": name,
  "mimeType": "application/vnd.google-apps.folder",
  }
  if parent_id:
    metadata["parents"] = [parent_id]
    folder = service.files().create(body=metadata, fields="id").execute()
    folder_id = folder["id"]
    logger.info(f"Created folder '{name}' (id={folder_id}, parent={parent_id})")
    return folder_id


def ensure_folder_structure(year: int, month: int) -> str:
  """
  Ensure the full folder path exists:
  Cotizaciones Panelin / 2026 / 03 - Marzo /
  Returns the month folder ID.
  """
  global _root_folder_id

if not _root_folder_id:
  _root_folder_id = _find_folder(ROOT_FOLDER_NAME)
  if not _root_folder_id:
    _root_folder_id = _create_folder(ROOT_FOLDER_NAME)
    logger.info(f"Created root folder: {ROOT_FOLDER_NAME}")

year_name = str(year)
year_id = _find_folder(year_name, _root_folder_id)
if not year_id:
  year_id = _create_folder(year_name, _root_folder_id)

month_name = f"{month:02d} - {MESES.get(month, str(month))}"
month_id = _find_folder(month_name, year_id)
if not month_id:
  month_id = _create_folder(month_name, year_id)

return month_id


def upload_pdf(pdf_bytes: bytes, filename: str, folder_id: str) -> Tuple[str, str, str]:
  """
  Upload PDF bytes to a Drive folder.
  Returns: (file_id, view_url, download_url)
  """
  service = get_drive_service()
  file_metadata = {
  "name": filename,
  "parents": [folder_id],
  "mimeType": "application/pdf",
  }
  media = MediaIoBaseUpload(
  io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=False
  )
  uploaded = service.files().create(
  body=file_metadata, media_body=media,
  fields="id, webViewLink, webContentLink"
  ).execute()

file_id = uploaded["id"]
view_url = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
download_url = f"https://drive.google.com/uc?id={file_id}&export=download"

try:
  service.permissions().create(
    fileId=file_id,
    body={"role": "reader", "type": "anyone"},
    fields="id"
  ).execute()
  logger.info(f"Set public read permission on {file_id}")
except Exception as e:
  logger.warning(f"Could not set public permission: {e}")

logger.info(f"Uploaded PDF: {filename} -> {file_id}")
return file_id, view_url, download_url


def get_drive_path(year: int, month: int, filename: str) -> str:
  """Return the human-readable Drive path string."""
  month_name = f"{month:02d} - {MESES.get(month, str(month))}"
  return f"{ROOT_FOLDER_NAME}/{year}/{month_name}/{filename}"


def generate_doc_number(prefix: str = "BMC") -> str:
  """Generate sequential document number: BMC-20260303-001"""
  now = datetime.now()
  date_part = now.strftime("%Y%m%d")
  seq = (now.hour * 3600 + now.minute * 60 + now.second) % 999 + 1
  return f"{prefix}-{date_part}-{seq:03d}"


def sanitize_filename(name: str) -> str:
  """Sanitize a string for use in filenames."""
  replacements = {
  "\u00e1": "a", "\u00e9": "e", "\u00ed": "i", "\u00f3": "o", "\u00fa": "u",
  "\u00f1": "n", "\u00c1": "A", "\u00c9": "E", "\u00cd": "I", "\u00d3": "O",
  "\u00da": "U", "\u00d1": "N",
  }
  for old, new in replacements.items():
    name = name.replace(old, new)
    name = re.sub(r"[^\w\s\-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:50]
