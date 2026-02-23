"""Tests for KB Architecture API routes."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestCreateVersion:
    """Test POST /api/kb/architecture."""

    async def test_create_version_success(
        self, client, api_headers, create_version_payload
    ):
        resp = await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["ok"] is True
        assert data["version"]["version_number"] == 1
        assert data["version"]["is_active"] is True
        assert len(data["version"]["modules"]) == 3
        assert len(data["version"]["checksum"]) == 64

    async def test_create_version_no_api_key(self, client, create_version_payload):
        resp = await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
        )
        assert resp.status_code == 401

    async def test_create_version_wrong_password(
        self, client, api_headers, create_version_payload
    ):
        create_version_payload["password"] = "wrong-password"
        resp = await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        assert resp.status_code == 403

    async def test_create_version_no_password(
        self, client, api_headers, sample_modules
    ):
        resp = await client.post(
            "/api/kb/architecture",
            json={
                "description": "Test",
                "author": "admin",
                "modules": sample_modules,
            },
            headers=api_headers,
        )
        assert resp.status_code == 422  # Pydantic validation error

    async def test_create_version_duplicate_modules(
        self, client, api_headers
    ):
        payload = {
            "version_type": "full_snapshot",
            "description": "Duplicates",
            "author": "admin",
            "modules": [
                {"module_name": "core", "module_data": {"a": 1}},
                {"module_name": "core", "module_data": {"b": 2}},
            ],
            "password": "test-password",
        }
        resp = await client.post(
            "/api/kb/architecture",
            json=payload,
            headers=api_headers,
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestGetActiveVersion:
    """Test GET /api/kb/architecture/active."""

    async def test_get_active_none(self, client, api_headers):
        resp = await client.get(
            "/api/kb/architecture/active", headers=api_headers
        )
        assert resp.status_code == 404

    async def test_get_active_after_create(
        self, client, api_headers, create_version_payload
    ):
        await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        resp = await client.get(
            "/api/kb/architecture/active", headers=api_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["version"]["is_active"] is True

    async def test_get_active_no_api_key(self, client):
        resp = await client.get("/api/kb/architecture/active")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestGetVersionById:
    """Test GET /api/kb/architecture/{version_id}."""

    async def test_get_by_id(
        self, client, api_headers, create_version_payload
    ):
        create_resp = await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        version_id = create_resp.json()["version"]["version_id"]

        resp = await client.get(
            f"/api/kb/architecture/{version_id}", headers=api_headers
        )
        assert resp.status_code == 200
        assert resp.json()["version"]["version_id"] == version_id

    async def test_get_nonexistent_id(self, client, api_headers):
        import uuid

        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/kb/architecture/{fake_id}", headers=api_headers
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestListVersions:
    """Test GET /api/kb/architecture/versions."""

    async def test_list_empty(self, client, api_headers):
        resp = await client.get(
            "/api/kb/architecture/versions", headers=api_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["versions"] == []
        assert data["total"] == 0

    async def test_list_with_versions(
        self, client, api_headers, create_version_payload
    ):
        # Create 2 versions
        await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        create_version_payload["description"] = "Version 2"
        await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )

        resp = await client.get(
            "/api/kb/architecture/versions", headers=api_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["versions"]) == 2


@pytest.mark.asyncio
class TestRollback:
    """Test POST /api/kb/architecture/rollback."""

    async def test_rollback_success(
        self, client, api_headers, create_version_payload
    ):
        # Create V1
        r1 = await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        v1_id = r1.json()["version"]["version_id"]

        # Create V2
        create_version_payload["description"] = "V2"
        await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )

        # Rollback to V1
        resp = await client.post(
            "/api/kb/architecture/rollback",
            json={
                "target_version_id": v1_id,
                "reason": "Testing rollback",
                "author": "admin",
                "password": "test-password",
            },
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["version"]["version_id"] == v1_id

        # Verify active is now V1
        active = await client.get(
            "/api/kb/architecture/active", headers=api_headers
        )
        assert active.json()["version"]["version_id"] == v1_id

    async def test_rollback_wrong_password(
        self, client, api_headers
    ):
        import uuid

        resp = await client.post(
            "/api/kb/architecture/rollback",
            json={
                "target_version_id": str(uuid.uuid4()),
                "reason": "Testing",
                "author": "admin",
                "password": "wrong",
            },
            headers=api_headers,
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestAuditLog:
    """Test GET /api/kb/architecture/audit."""

    async def test_audit_log_records_creation(
        self, client, api_headers, create_version_payload
    ):
        await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        resp = await client.get(
            "/api/kb/architecture/audit", headers=api_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(e["action"] == "version_created" for e in data["entries"])

    async def test_audit_log_filter(
        self, client, api_headers, create_version_payload
    ):
        await client.post(
            "/api/kb/architecture",
            json=create_version_payload,
            headers=api_headers,
        )
        resp = await client.get(
            "/api/kb/architecture/audit?action=version_created",
            headers=api_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["action"] == "version_created" for e in data["entries"])
