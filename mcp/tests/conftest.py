"""Shared pytest configuration for MCP test suite."""

from __future__ import annotations

import os


# Ensure password-protected handlers can be exercised in tests without relying
# on insecure defaults.
os.environ.setdefault("WOLF_KB_WRITE_PASSWORD", "test-password")
