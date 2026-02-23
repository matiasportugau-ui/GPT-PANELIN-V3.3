"""Tests for KB Architecture service layer."""

from __future__ import annotations

import pytest
import pytest_asyncio

from wolf_api.kb_schemas import CreateVersionRequest, RollbackRequest
from wolf_api.kb_service import (
    compute_module_checksum,
    compute_version_checksum,
    create_version,
    get_active_version,
    get_version_by_id,
    list_versions,
    rollback_version,
    get_audit_log,
)


class TestChecksums:
    """Test checksum computation functions."""

    def test_module_checksum_deterministic(self):
        data = {"b": 2, "a": 1, "c": {"z": 26, "y": 25}}
        c1 = compute_module_checksum(data)
        c2 = compute_module_checksum(data)
        assert c1 == c2

    def test_module_checksum_key_order_irrelevant(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert compute_module_checksum(d1) == compute_module_checksum(d2)

    def test_module_checksum_different_data(self):
        d1 = {"a": 1}
        d2 = {"a": 2}
        assert compute_module_checksum(d1) != compute_module_checksum(d2)

    def test_version_checksum_deterministic(self):
        checksums = ["abc123", "def456", "ghi789"]
        c1 = compute_version_checksum(checksums)
        c2 = compute_version_checksum(checksums)
        assert c1 == c2

    def test_version_checksum_order_irrelevant(self):
        c1 = compute_version_checksum(["abc", "def", "ghi"])
        c2 = compute_version_checksum(["ghi", "abc", "def"])
        assert c1 == c2

    def test_checksum_is_sha256_hex(self):
        checksum = compute_module_checksum({"test": True})
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)


@pytest.mark.asyncio
class TestCreateVersion:
    """Test version creation."""

    async def test_create_first_version(self, test_session, sample_modules):
        request = CreateVersionRequest(
            version_type="full_snapshot",
            description="Initial KB architecture",
            author="test_admin",
            modules=sample_modules,
            password="test-password",
        )
        version = await create_version(test_session, request)
        await test_session.commit()

        assert version.version_number == 1
        assert version.is_active is True
        assert version.author == "test_admin"
        assert len(version.modules) == 3
        assert len(version.checksum) == 64

    async def test_create_second_version_deactivates_first(
        self, test_session, sample_modules
    ):
        req1 = CreateVersionRequest(
            version_type="full_snapshot",
            description="Version 1",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        v1 = await create_version(test_session, req1)
        await test_session.commit()

        req2 = CreateVersionRequest(
            version_type="partial_update",
            description="Version 2",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        v2 = await create_version(test_session, req2)
        await test_session.commit()

        assert v2.version_number == 2
        assert v2.is_active is True

        # Refresh v1 to check it was deactivated
        await test_session.refresh(v1)
        assert v1.is_active is False

    async def test_version_numbers_monotonic(self, test_session, sample_modules):
        for i in range(3):
            req = CreateVersionRequest(
                version_type="full_snapshot",
                description=f"Version {i + 1}",
                author="admin",
                modules=sample_modules,
                password="pw",
            )
            v = await create_version(test_session, req)
            await test_session.commit()
            assert v.version_number == i + 1

    async def test_audit_log_created_on_version_creation(
        self, test_session, sample_modules
    ):
        req = CreateVersionRequest(
            version_type="full_snapshot",
            description="Audited version",
            author="auditor",
            modules=sample_modules,
            password="pw",
        )
        await create_version(test_session, req)
        await test_session.commit()

        entries = await get_audit_log(test_session)
        assert len(entries) == 1
        assert entries[0].action == "version_created"
        assert entries[0].actor == "auditor"


@pytest.mark.asyncio
class TestGetVersion:
    """Test version retrieval."""

    async def test_get_active_version(self, test_session, sample_modules):
        req = CreateVersionRequest(
            version_type="full_snapshot",
            description="Active version",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        created = await create_version(test_session, req)
        await test_session.commit()

        active = await get_active_version(test_session)
        assert active is not None
        assert active.version_id == created.version_id
        assert len(active.modules) == 3

    async def test_get_active_version_none(self, test_session):
        active = await get_active_version(test_session)
        assert active is None

    async def test_get_version_by_id(self, test_session, sample_modules):
        req = CreateVersionRequest(
            version_type="full_snapshot",
            description="By ID",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        created = await create_version(test_session, req)
        await test_session.commit()

        found = await get_version_by_id(test_session, created.version_id)
        assert found is not None
        assert found.description == "By ID"

    async def test_list_versions(self, test_session, sample_modules):
        for i in range(3):
            req = CreateVersionRequest(
                version_type="full_snapshot",
                description=f"Version {i + 1} for testing",
                author="admin",
                modules=sample_modules,
                password="pw",
            )
            await create_version(test_session, req)
            await test_session.commit()

        versions = await list_versions(test_session)
        assert len(versions) == 3


@pytest.mark.asyncio
class TestRollback:
    """Test version rollback."""

    async def test_rollback_switches_active(self, test_session, sample_modules):
        req1 = CreateVersionRequest(
            version_type="full_snapshot",
            description="Version 1 initial",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        v1 = await create_version(test_session, req1)
        await test_session.commit()

        req2 = CreateVersionRequest(
            version_type="full_snapshot",
            description="Version 2 update",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        await create_version(test_session, req2)
        await test_session.commit()

        rollback_req = RollbackRequest(
            target_version_id=v1.version_id,
            reason="Reverting to V1",
            author="admin",
            password="pw",
        )
        rolled = await rollback_version(test_session, rollback_req)
        await test_session.commit()

        assert rolled.version_id == v1.version_id
        active = await get_active_version(test_session)
        assert active.version_id == v1.version_id

    async def test_rollback_nonexistent_raises(self, test_session):
        import uuid

        rollback_req = RollbackRequest(
            target_version_id=uuid.uuid4(),
            reason="Should fail",
            author="admin",
            password="pw",
        )
        with pytest.raises(ValueError, match="not found"):
            await rollback_version(test_session, rollback_req)

    async def test_rollback_creates_audit_entry(
        self, test_session, sample_modules
    ):
        req1 = CreateVersionRequest(
            version_type="full_snapshot",
            description="Version 1 audit test",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        v1 = await create_version(test_session, req1)
        await test_session.commit()

        req2 = CreateVersionRequest(
            version_type="full_snapshot",
            description="Version 2 audit test",
            author="admin",
            modules=sample_modules,
            password="pw",
        )
        await create_version(test_session, req2)
        await test_session.commit()

        rollback_req = RollbackRequest(
            target_version_id=v1.version_id,
            reason="Testing rollback audit",
            author="auditor",
            password="pw",
        )
        await rollback_version(test_session, rollback_req)
        await test_session.commit()

        entries = await get_audit_log(test_session, action_filter="rollback")
        assert len(entries) == 1
        assert entries[0].actor == "auditor"
        assert entries[0].details["reason"] == "Testing rollback audit"
