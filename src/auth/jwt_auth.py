"""
Panelin v5.0 — JWT Authentication & RBAC
============================================

Replaces the simple API key auth with JWT-based authentication.
Supports role-based access control for different user types.

Roles:
    - admin: Full access to all endpoints and agent management
    - sales: Quotation creation, customer management, sheets access
    - viewer: Read-only access to quotations and catalog
    - agent: Service-to-service authentication (MCP, internal APIs)
"""

from __future__ import annotations

import hmac
import time
import json
import logging
from typing import Optional
from dataclasses import dataclass

from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


@dataclass
class TokenPayload:
    sub: str
    role: str
    exp: float
    iat: float
    iss: str = "panelin"


ROLE_PERMISSIONS = {
    "admin": {"*"},
    "sales": {
        "quote:create", "quote:read", "quote:update",
        "customer:create", "customer:read", "customer:update",
        "sheets:read", "sheets:write",
        "pdf:generate",
        "catalog:read",
    },
    "viewer": {
        "quote:read",
        "customer:read",
        "sheets:read",
        "catalog:read",
    },
    "agent": {
        "quote:create", "quote:read",
        "catalog:read",
        "mcp:call",
    },
}


def _encode_jwt(payload: dict, secret: str) -> str:
    """Minimal JWT encoding (HS256) without external dependencies."""
    import base64
    import hashlib

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()

    signing_input = f"{header}.{body}"
    signature = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{header}.{body}.{sig_b64}"


def _decode_jwt(token: str, secret: str) -> dict:
    """Minimal JWT decoding with signature verification."""
    import base64
    import hashlib

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    header_b64, body_b64, sig_b64 = parts

    signing_input = f"{header_b64}.{body_b64}"
    expected_sig = hmac.new(
        secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()

    if not hmac.compare_digest(sig_b64, expected_b64):
        raise ValueError("Invalid signature")

    padding = 4 - len(body_b64) % 4
    body_bytes = base64.urlsafe_b64decode(body_b64 + "=" * padding)
    payload = json.loads(body_bytes)

    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expired")

    return payload


def create_token(
    subject: str,
    role: str = "viewer",
    expires_in: int = 86400,
) -> str:
    """Create a JWT token for a user/service.

    Args:
        subject: User ID or service name
        role: One of 'admin', 'sales', 'viewer', 'agent'
        expires_in: Token validity in seconds (default 24h)

    Returns:
        JWT token string.
    """
    settings = get_settings()
    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET not configured")

    now = time.time()
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
        "iss": "panelin",
    }
    return _encode_jwt(payload, settings.jwt_secret)


def verify_token(token: str) -> TokenPayload:
    """Verify and decode a JWT token."""
    settings = get_settings()
    if not settings.jwt_secret:
        raise ValueError("JWT_SECRET not configured")

    payload = _decode_jwt(token, settings.jwt_secret)

    return TokenPayload(
        sub=payload["sub"],
        role=payload.get("role", "viewer"),
        exp=payload["exp"],
        iat=payload["iat"],
        iss=payload.get("iss", "panelin"),
    )


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> TokenPayload:
    """FastAPI dependency for JWT authentication.

    Falls back to X-API-Key header for backward compatibility.
    """
    settings = get_settings()

    if credentials and credentials.credentials:
        try:
            return verify_token(credentials.credentials)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

    raise HTTPException(status_code=401, detail="Authentication required")


def require_permission(permission: str):
    """FastAPI dependency factory for permission checks."""

    async def _check(
        token: TokenPayload = Security(require_auth),
    ) -> TokenPayload:
        if not has_permission(token.role, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' required (role: {token.role})",
            )
        return token

    return _check
