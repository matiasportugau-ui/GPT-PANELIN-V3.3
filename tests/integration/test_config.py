"""
Tests for the configuration module.
"""

from __future__ import annotations

import os
import pytest


class TestPanelinSettings:
    def test_default_settings(self):
        from src.core.config import PanelinSettings
        settings = PanelinSettings()
        assert settings.app_name == "Panelin"
        assert settings.app_version == "5.0.0"
        assert settings.environment == "development"
        assert settings.port == 8080

    def test_db_url_construction(self):
        from src.core.config import PanelinSettings
        settings = PanelinSettings(
            DB_HOST="localhost",
            DB_PORT=5432,
            DB_NAME="testdb",
            DB_USER="testuser",
            DB_PASSWORD="testpass",
        )
        assert "testuser:testpass" in settings.db_url
        assert "testdb" in settings.db_url

    def test_db_url_cloud_sql(self):
        from src.core.config import PanelinSettings
        settings = PanelinSettings(
            DB_CONNECTION_NAME="project:region:instance",
            DB_NAME="testdb",
            DB_USER="testuser",
            DB_PASSWORD="testpass",
        )
        assert "/cloudsql/project:region:instance" in settings.db_url

    def test_cors_origins_parsing(self):
        from src.core.config import PanelinSettings
        settings = PanelinSettings(
            cors_allowed_origins="http://localhost:3000,https://app.agno.com"
        )
        origins = settings.cors_origins_list
        assert len(origins) == 2
        assert "http://localhost:3000" in origins

    def test_invalid_environment(self):
        from src.core.config import PanelinSettings
        with pytest.raises(Exception):
            PanelinSettings(environment="invalid")
