"""
Tests for src/core/config.py
"""

import os
import pytest


class TestDatabaseSettings:
    def test_default_url(self):
        from src.core.config import DatabaseSettings
        db = DatabaseSettings()
        assert "postgresql+psycopg://" in db.url
        assert "localhost" in db.url

    def test_cloud_sql_url(self):
        from src.core.config import DatabaseSettings
        db = DatabaseSettings(
            user="admin",
            password="secret",
            name="mydb",
            cloud_sql_connection="project:us-central1:instance",
        )
        assert "/cloudsql/" in db.url
        assert "project:us-central1:instance" in db.url


class TestSecuritySettings:
    def test_cors_origins_parsing(self):
        from src.core.config import SecuritySettings
        sec = SecuritySettings(cors_origins="http://a.com,http://b.com")
        assert sec.cors_origins_list == ["http://a.com", "http://b.com"]

    def test_empty_cors(self):
        from src.core.config import SecuritySettings
        sec = SecuritySettings(cors_origins="")
        assert sec.cors_origins_list == []
