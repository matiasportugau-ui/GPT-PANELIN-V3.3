"""Handlers for project file read/write MCP tools.

Two tools for direct project file operations:
- write_file: Create or overwrite project files (password required)
- read_file: Read project file contents (no password required)

Write operations require the KB write password for authorization.
Read operations do not require a password (mirrors lookup_customer precedent).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from mcp_tools.contracts import (
    CONTRACT_VERSION,
    WRITE_FILE_ERROR_CODES,
    READ_FILE_ERROR_CODES,
)

logger = logging.getLogger(__name__)

# Project root — same derivation as governance.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# KB write password — reuse the same env var as wolf_kb_write.py
KB_WRITE_PASSWORD = os.getenv("WOLF_KB_WRITE_PASSWORD", "mywolfy")

# Maximum file size: 1 MB (prevents accidental large writes)
MAX_FILE_SIZE_BYTES = 1_048_576

# Maximum read size: 2 MB
MAX_READ_SIZE_BYTES = 2_097_152

# Blocked path patterns (compiled regexes for efficiency)
BLOCKED_PATTERNS = [
    re.compile(r"(^|/)\.env($|\..*)"),            # .env, .env.local, etc.
    re.compile(r"(^|/)\.git(/|$)"),                # .git directory
    re.compile(r"(^|/)\.github(/|$)"),             # .github directory
    re.compile(r"(^|/)node_modules(/|$)"),         # node_modules
    re.compile(r"(^|/)__pycache__(/|$)"),          # Python cache
    re.compile(r"(^|/)venv(/|$)"),                 # Virtual environments
    re.compile(r"(^|/)\.vscode(/|$)"),             # IDE configs
    re.compile(r"(^|/)\.idea(/|$)"),               # IDE configs
    re.compile(r"(^|/)terraform(/|$)"),            # Infrastructure-as-code
    re.compile(r"(^|/)docker-compose\.yml$"),       # Docker compose
    re.compile(r"(^|/)Dockerfile$"),               # Dockerfile
    re.compile(r"(^|/)cloudbuild\.yaml$"),          # Cloud Build
]

# Blocked filename patterns (secrets, credentials, keys)
BLOCKED_FILENAMES = [
    re.compile(r".*credential.*", re.IGNORECASE),
    re.compile(r".*secret.*", re.IGNORECASE),
    re.compile(r".*\.pem$", re.IGNORECASE),
    re.compile(r".*\.key$", re.IGNORECASE),
    re.compile(r".*\.pfx$", re.IGNORECASE),
    re.compile(r".*\.p12$", re.IGNORECASE),
    re.compile(r".*id_rsa.*", re.IGNORECASE),
    re.compile(r".*id_ed25519.*", re.IGNORECASE),
]

# Blocked binary extensions
BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a",
    ".pyc", ".pyo", ".class", ".jar", ".war",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def _validate_password(arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Validate the KB write password. Returns error envelope or None if valid."""
    password = arguments.get("password")
    if not password:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WRITE_FILE_ERROR_CODES["PASSWORD_REQUIRED"],
                "message": "KB write password is required for write operations.",
            },
        }
    if password != KB_WRITE_PASSWORD:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WRITE_FILE_ERROR_CODES["INVALID_PASSWORD"],
                "message": "Invalid KB write password.",
            },
        }
    return None


def _validate_path(
    file_path: str,
    error_codes: dict[str, str],
) -> tuple[Path | None, dict[str, Any] | None]:
    """Validate and resolve a file path.

    Returns (resolved_path, None) if valid, or (None, error_envelope) if not.
    """
    if not file_path or not file_path.strip():
        return None, {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": error_codes["INVALID_PATH"],
                "message": "file_path is required and cannot be empty.",
            },
        }

    # Block path traversal: reject any ".." component
    if ".." in file_path:
        return None, {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": error_codes["PATH_TRAVERSAL"],
                "message": "Path traversal ('..') is not allowed.",
            },
        }

    # Resolve and ensure within project root
    resolved = (PROJECT_ROOT / file_path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return None, {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": error_codes["PATH_TRAVERSAL"],
                "message": "Resolved path is outside the project root.",
            },
        }

    # Check against blocked path patterns
    relative_str = str(resolved.relative_to(PROJECT_ROOT))
    for pattern in BLOCKED_PATTERNS:
        if pattern.search(relative_str):
            return None, {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": error_codes["BLOCKED_PATH"],
                    "message": f"Access to '{relative_str}' is blocked by security policy.",
                },
            }

    # Check against blocked filename patterns
    for pattern in BLOCKED_FILENAMES:
        if pattern.match(resolved.name):
            return None, {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": error_codes["BLOCKED_PATH"],
                    "message": (
                        f"File name '{resolved.name}' matches a blocked pattern "
                        f"(secrets/credentials)."
                    ),
                },
            }

    return resolved, None


async def handle_write_file(
    arguments: dict[str, Any],
    legacy_format: bool = False,
) -> dict[str, Any]:
    """Write or update a project file.

    Requires KB write password. Validates path safety before writing.
    Creates parent directories if needed.

    Args:
        arguments: Tool arguments containing file_path, content, password
        legacy_format: Unused, kept for handler interface consistency

    Returns:
        v1 contract envelope with file_path, bytes_written, created
    """
    # 1. Validate password
    error = _validate_password(arguments)
    if error:
        return error

    file_path = arguments.get("file_path", "")
    content = arguments.get("content")

    if content is None:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WRITE_FILE_ERROR_CODES["INTERNAL_ERROR"],
                "message": "content is required.",
            },
        }

    # 2. Validate path
    resolved, path_error = _validate_path(file_path, WRITE_FILE_ERROR_CODES)
    if path_error:
        return path_error

    # 3. Check binary extension
    if resolved.suffix.lower() in BINARY_EXTENSIONS:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WRITE_FILE_ERROR_CODES["BINARY_NOT_ALLOWED"],
                "message": f"Cannot write binary file type '{resolved.suffix}'.",
            },
        }

    # 4. Check content size
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WRITE_FILE_ERROR_CODES["FILE_TOO_LARGE"],
                "message": (
                    f"Content exceeds maximum size "
                    f"({MAX_FILE_SIZE_BYTES} bytes)."
                ),
            },
        }

    try:
        # 5. Create parent directories if needed
        created = not resolved.is_file()
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # 6. Write file
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)

        relative_path = str(resolved.relative_to(PROJECT_ROOT))
        logger.info(
            "write_file: %s %s (%d bytes)",
            "created" if created else "updated",
            relative_path,
            len(content_bytes),
        )

        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "file_path": relative_path,
            "bytes_written": len(content_bytes),
            "created": created,
        }
    except Exception as exc:
        logger.exception("write_file failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": WRITE_FILE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }


async def handle_read_file(
    arguments: dict[str, Any],
    legacy_format: bool = False,
) -> dict[str, Any]:
    """Read a project file's contents.

    No password required — this is a read-only operation.

    Args:
        arguments: Tool arguments containing file_path
        legacy_format: Unused, kept for handler interface consistency

    Returns:
        v1 contract envelope with file_path, content, size_bytes
    """
    file_path = arguments.get("file_path", "")

    # 1. Validate path
    resolved, path_error = _validate_path(file_path, READ_FILE_ERROR_CODES)
    if path_error:
        return path_error

    # 2. Check binary extension
    if resolved.suffix.lower() in BINARY_EXTENSIONS:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": READ_FILE_ERROR_CODES["BINARY_NOT_ALLOWED"],
                "message": f"Cannot read binary file type '{resolved.suffix}'.",
            },
        }

    # 3. Check file exists
    if not resolved.is_file():
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": READ_FILE_ERROR_CODES["FILE_NOT_FOUND"],
                "message": f"File not found: '{file_path}'.",
            },
        }

    try:
        # 4. Check file size before reading
        file_size = resolved.stat().st_size
        if file_size > MAX_READ_SIZE_BYTES:
            return {
                "ok": False,
                "contract_version": CONTRACT_VERSION,
                "error": {
                    "code": READ_FILE_ERROR_CODES["FILE_TOO_LARGE"],
                    "message": (
                        f"File size ({file_size} bytes) exceeds maximum "
                        f"read size ({MAX_READ_SIZE_BYTES} bytes)."
                    ),
                },
            }

        # 5. Read file
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()

        relative_path = str(resolved.relative_to(PROJECT_ROOT))
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "file_path": relative_path,
            "content": content,
            "size_bytes": file_size,
        }
    except UnicodeDecodeError:
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": READ_FILE_ERROR_CODES["BINARY_NOT_ALLOWED"],
                "message": "File appears to be binary and cannot be read as text.",
            },
        }
    except Exception as exc:
        logger.exception("read_file failed")
        return {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "error": {
                "code": READ_FILE_ERROR_CODES["INTERNAL_ERROR"],
                "message": str(exc),
            },
        }
