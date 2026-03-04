"""Test file operations handlers return v1 contract envelopes.

Validates that write_file and read_file handlers:
1. Enforce password validation for write operations
2. Allow read_file without password
3. Block path traversal attacks
4. Block sensitive files (.env, .git/, credentials)
5. Block binary file extensions
6. Enforce file size limits
7. Return proper v1 contract envelope structures

These tests run in CI via .github/workflows/mcp-tests.yml
"""

import pytest

from mcp.handlers.file_ops import (
    handle_write_file,
    handle_read_file,
    KB_WRITE_PASSWORD,
    MAX_FILE_SIZE_BYTES,
)
from mcp_tools.contracts import (
    WRITE_FILE_ERROR_CODES,
    READ_FILE_ERROR_CODES,
)


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """Override PROJECT_ROOT to tmp_path for safe testing."""
    monkeypatch.setattr("mcp.handlers.file_ops.PROJECT_ROOT", tmp_path)
    return tmp_path


class TestWriteFilePassword:
    """Test write_file password enforcement."""

    @pytest.mark.asyncio
    async def test_missing_password_returns_error(self, project_root):
        result = await handle_write_file({
            "file_path": "test_output.txt",
            "content": "hello",
        })
        assert result["ok"] is False
        assert result["contract_version"] == "v1"
        assert result["error"]["code"] == "PASSWORD_REQUIRED"

    @pytest.mark.asyncio
    async def test_wrong_password_returns_error(self, project_root):
        result = await handle_write_file({
            "file_path": "test_output.txt",
            "content": "hello",
            "password": "wrongpassword",
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PASSWORD"

    @pytest.mark.asyncio
    async def test_missing_content_returns_error(self, project_root):
        result = await handle_write_file({
            "file_path": "test_output.txt",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INTERNAL_ERROR"


class TestWriteFilePathSafety:
    """Test write_file path safety restrictions."""

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": "../../etc/passwd",
            "content": "hacked",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "PATH_TRAVERSAL"

    @pytest.mark.asyncio
    async def test_env_file_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": ".env",
            "content": "SECRET=hack",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_env_production_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": ".env.production",
            "content": "SECRET=hack",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_git_directory_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": ".git/config",
            "content": "hacked",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_credential_file_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": "credentials.json",
            "content": "{}",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_pem_file_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": "server.pem",
            "content": "cert",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_binary_extension_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": "output.exe",
            "content": "binary",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BINARY_NOT_ALLOWED"

    @pytest.mark.asyncio
    async def test_file_too_large(self, project_root):
        result = await handle_write_file({
            "file_path": "large_file.txt",
            "content": "x" * (MAX_FILE_SIZE_BYTES + 1),
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "FILE_TOO_LARGE"

    @pytest.mark.asyncio
    async def test_empty_path_rejected(self, project_root):
        result = await handle_write_file({
            "file_path": "",
            "content": "hello",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PATH"

    @pytest.mark.asyncio
    async def test_terraform_directory_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": "terraform/main.tf",
            "content": "resource {}",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_dockerfile_blocked(self, project_root):
        result = await handle_write_file({
            "file_path": "Dockerfile",
            "content": "FROM python:3.11",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"


class TestWriteFileSuccess:
    """Test successful write_file operations."""

    @pytest.mark.asyncio
    async def test_create_new_file(self, project_root):
        result = await handle_write_file({
            "file_path": "test_subdir/hello.txt",
            "content": "Hello, World!",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert result["created"] is True
        assert result["bytes_written"] == 13
        assert (project_root / "test_subdir" / "hello.txt").read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, project_root):
        (project_root / "existing.txt").write_text("old content")
        result = await handle_write_file({
            "file_path": "existing.txt",
            "content": "new content",
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["created"] is False
        assert (project_root / "existing.txt").read_text() == "new content"

    @pytest.mark.asyncio
    async def test_write_json_file(self, project_root):
        content = '{"price": 105.50, "product": "ISODEC_EPS_100"}'
        result = await handle_write_file({
            "file_path": "data/pricing_update.json",
            "content": content,
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["created"] is True
        assert (project_root / "data" / "pricing_update.json").read_text() == content

    @pytest.mark.asyncio
    async def test_write_python_file(self, project_root):
        content = 'print("hello")\n'
        result = await handle_write_file({
            "file_path": "scripts/test_script.py",
            "content": content,
            "password": KB_WRITE_PASSWORD,
        })
        assert result["ok"] is True
        assert result["file_path"] == "scripts/test_script.py"


class TestReadFile:
    """Test read_file handler."""

    @pytest.mark.asyncio
    async def test_no_password_needed(self, project_root):
        (project_root / "readme.md").write_text("# Hello")
        result = await handle_read_file({"file_path": "readme.md"})
        assert result["ok"] is True
        assert result["contract_version"] == "v1"
        assert result["content"] == "# Hello"
        assert result["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_file_not_found(self, project_root):
        result = await handle_read_file({"file_path": "nonexistent.txt"})
        assert result["ok"] is False
        assert result["error"]["code"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, project_root):
        result = await handle_read_file({"file_path": "../../etc/passwd"})
        assert result["ok"] is False
        assert result["error"]["code"] == "PATH_TRAVERSAL"

    @pytest.mark.asyncio
    async def test_env_blocked(self, project_root):
        result = await handle_read_file({"file_path": ".env"})
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_binary_blocked(self, project_root):
        result = await handle_read_file({"file_path": "image.png"})
        assert result["ok"] is False
        assert result["error"]["code"] == "BINARY_NOT_ALLOWED"

    @pytest.mark.asyncio
    async def test_empty_path_rejected(self, project_root):
        result = await handle_read_file({"file_path": ""})
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_PATH"

    @pytest.mark.asyncio
    async def test_read_json_file(self, project_root):
        content = '{"key": "value"}'
        (project_root / "data.json").write_text(content)
        result = await handle_read_file({"file_path": "data.json"})
        assert result["ok"] is True
        assert result["content"] == content
        assert result["file_path"] == "data.json"

    @pytest.mark.asyncio
    async def test_git_directory_blocked(self, project_root):
        result = await handle_read_file({"file_path": ".git/config"})
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"

    @pytest.mark.asyncio
    async def test_credential_file_blocked(self, project_root):
        result = await handle_read_file({"file_path": "credentials.json"})
        assert result["ok"] is False
        assert result["error"]["code"] == "BLOCKED_PATH"


class TestWriteReadRoundTrip:
    """Test write then read produces consistent results."""

    @pytest.mark.asyncio
    async def test_write_then_read(self, project_root):
        content = "Line 1\nLine 2\nLine 3\n"
        write_result = await handle_write_file({
            "file_path": "roundtrip_test.txt",
            "content": content,
            "password": KB_WRITE_PASSWORD,
        })
        assert write_result["ok"] is True

        read_result = await handle_read_file({"file_path": "roundtrip_test.txt"})
        assert read_result["ok"] is True
        assert read_result["content"] == content


class TestErrorCodeRegistries:
    """Validate error codes are properly registered."""

    def test_write_file_error_codes_complete(self):
        expected = {
            "PASSWORD_REQUIRED", "INVALID_PASSWORD",
            "INVALID_PATH", "PATH_TRAVERSAL", "BLOCKED_PATH",
            "BINARY_NOT_ALLOWED", "FILE_TOO_LARGE", "INTERNAL_ERROR",
        }
        assert set(WRITE_FILE_ERROR_CODES.keys()) == expected

    def test_read_file_error_codes_complete(self):
        expected = {
            "INVALID_PATH", "PATH_TRAVERSAL", "BLOCKED_PATH",
            "BINARY_NOT_ALLOWED", "FILE_TOO_LARGE", "FILE_NOT_FOUND",
            "INTERNAL_ERROR",
        }
        assert set(READ_FILE_ERROR_CODES.keys()) == expected
