"""
Tests for JWT authentication.
"""

from __future__ import annotations

import os
import time
import pytest


class TestJWTAuth:
    @pytest.fixture(autouse=True)
    def setup_jwt_secret(self, monkeypatch):
        monkeypatch.setenv("PANELIN_JWT_SECRET", "test-secret-key-for-testing-only")
        from src.core.config import get_settings
        get_settings.cache_clear()

    def test_create_and_verify_token(self):
        from src.auth.jwt_auth import create_token, verify_token

        token = create_token(subject="test-user", role="sales", expires_in=3600)
        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 3

        payload = verify_token(token)
        assert payload.sub == "test-user"
        assert payload.role == "sales"
        assert payload.iss == "panelin"

    def test_expired_token(self):
        from src.auth.jwt_auth import create_token, verify_token

        token = create_token(subject="test-user", role="viewer", expires_in=-1)
        with pytest.raises(ValueError, match="expired"):
            verify_token(token)

    def test_invalid_signature(self):
        from src.auth.jwt_auth import create_token, verify_token

        token = create_token(subject="test-user", role="admin")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError, match="signature"):
            verify_token(tampered)

    def test_role_permissions(self):
        from src.auth.jwt_auth import has_permission

        assert has_permission("admin", "quote:create") is True
        assert has_permission("admin", "anything") is True
        assert has_permission("sales", "quote:create") is True
        assert has_permission("sales", "admin:delete") is False
        assert has_permission("viewer", "quote:read") is True
        assert has_permission("viewer", "quote:create") is False
