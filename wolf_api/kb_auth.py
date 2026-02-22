"""Authentication and authorization for KB Architecture API.

Implements:
- API key validation (X-API-Key header with hmac.compare_digest)
- Password protection for write operations
- Follows the same pattern as wolf_api/main.py:43-54
"""

from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

# Reuse the same env var and header name as the main wolf_api auth
WOLF_API_KEY = os.environ.get("WOLF_API_KEY", "")
KB_WRITE_PASSWORD = os.environ.get("KB_WRITE_PASSWORD", "mywolfy")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> None:
    """Validate API key from X-API-Key header.

    Raises HTTPException 503 if WOLF_API_KEY not configured,
    or 401 if key is missing/invalid.
    """
    if not WOLF_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not configured: WOLF_API_KEY is missing",
        )
    if not api_key or not hmac.compare_digest(api_key, WOLF_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )


def validate_write_password(password: str) -> None:
    """Validate KB write password. Raises HTTPException 403 on mismatch.

    Uses hmac.compare_digest to prevent timing attacks.
    """
    if not password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KB write password is required",
        )
    if not hmac.compare_digest(password, KB_WRITE_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid KB write password",
        )
