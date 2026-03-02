"""Tests for shortcuts (atajos) handler."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from mcp.handlers.shortcuts import (
    handle_shortcut_execute,
    handle_shortcut_manage,
)


def _tmp_shortcuts_file(shortcuts=None):
    """Create a temporary shortcuts file and patch the module constant."""
    data = {
        "version": "1.0.0",
        "shortcuts": shortcuts or [],
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp, ensure_ascii=False)
    tmp.close()
    return Path(tmp.name)


SAMPLE_SHORTCUT = {
    "id": "open-mcp-docs",
    "name": "open-mcp-docs",
    "prompt": "Navigate to MCP docs.",
    "start_url": "https://developers.openai.com/api/docs/guides/tools-connectors-mcp",
    "model": "haiku-4.5",
    "schedule": {"type": "once", "time": "09:00", "timezone": "UTC"},
    "enabled": True,
    "created_at": "2026-02-14T10:00:00Z",
    "tags": ["documentation", "mcp"],
}


# ── shortcut_execute tests ──────────────────────────────────────────


class TestShortcutExecute:

    @pytest.mark.asyncio
    async def test_execute_existing_shortcut(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_execute({"name": "open-mcp-docs"})
        assert result["ok"] is True
        assert result["shortcut"]["name"] == "open-mcp-docs"
        assert "Navigate" in result["shortcut"]["prompt"]
        assert result["shortcut"]["start_url"] is not None
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_execute_with_leading_slash(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_execute({"name": "/open-mcp-docs"})
        assert result["ok"] is True
        assert result["shortcut"]["name"] == "open-mcp-docs"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_execute_not_found(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_execute({"name": "nonexistent"})
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        assert "available_shortcuts" in result["error"]
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_execute_missing_name(self):
        tmp = _tmp_shortcuts_file()
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_execute({"name": ""})
        assert result["ok"] is False
        assert result["error"]["code"] == "MISSING_NAME"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_execute_disabled_shortcut(self):
        disabled = {**SAMPLE_SHORTCUT, "enabled": False}
        tmp = _tmp_shortcuts_file([disabled])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_execute({"name": "open-mcp-docs"})
        assert result["ok"] is False
        assert result["error"]["code"] == "DISABLED"
        tmp.unlink()


# ── shortcut_manage tests ───────────────────────────────────────────


class TestShortcutManage:

    @pytest.mark.asyncio
    async def test_list_shortcuts(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({"action": "list"})
        assert result["ok"] is True
        assert result["total"] == 1
        assert result["shortcuts"][0]["name"] == "open-mcp-docs"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_list_filter_by_tag(self):
        other = {**SAMPLE_SHORTCUT, "name": "other", "id": "other", "tags": ["other"]}
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT, other])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({"action": "list", "tag": "mcp"})
        assert result["ok"] is True
        assert result["total"] == 1
        assert result["shortcuts"][0]["name"] == "open-mcp-docs"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_create_shortcut(self):
        tmp = _tmp_shortcuts_file()
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "create",
                "name": "my-shortcut",
                "prompt": "Do something useful",
                "start_url": "https://example.com",
                "model": "haiku-4.5",
                "tags": ["test"],
            })
        assert result["ok"] is True
        assert result["shortcut"]["name"] == "my-shortcut"

        # Verify persistence
        with open(tmp, encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved["shortcuts"]) == 1
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_create_duplicate(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "create",
                "name": "open-mcp-docs",
                "prompt": "duplicate",
            })
        assert result["ok"] is False
        assert result["error"]["code"] == "DUPLICATE"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_create_missing_prompt(self):
        tmp = _tmp_shortcuts_file()
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "create",
                "name": "bad-shortcut",
            })
        assert result["ok"] is False
        assert result["error"]["code"] == "MISSING_PROMPT"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_update_shortcut(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "update",
                "name": "open-mcp-docs",
                "prompt": "Updated prompt",
                "model": "sonnet-4",
            })
        assert result["ok"] is True
        assert result["shortcut"]["prompt"] == "Updated prompt"
        assert result["shortcut"]["model"] == "sonnet-4"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        tmp = _tmp_shortcuts_file()
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "update",
                "name": "nonexistent",
                "prompt": "Updated",
            })
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_delete_shortcut(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "delete",
                "name": "open-mcp-docs",
            })
        assert result["ok"] is True

        with open(tmp, encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved["shortcuts"]) == 0
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        tmp = _tmp_shortcuts_file()
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({
                "action": "delete",
                "name": "nonexistent",
            })
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_enable_disable_shortcut(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            # Disable
            result = await handle_shortcut_manage({
                "action": "disable",
                "name": "open-mcp-docs",
            })
            assert result["ok"] is True
            assert "disabled" in result["message"]

            # Verify disabled
            result = await handle_shortcut_execute({"name": "open-mcp-docs"})
            assert result["ok"] is False
            assert result["error"]["code"] == "DISABLED"

            # Enable
            result = await handle_shortcut_manage({
                "action": "enable",
                "name": "open-mcp-docs",
            })
            assert result["ok"] is True
            assert "enabled" in result["message"]

            # Verify enabled
            result = await handle_shortcut_execute({"name": "open-mcp-docs"})
            assert result["ok"] is True
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        tmp = _tmp_shortcuts_file()
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({"action": "invalid"})
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_ACTION"
        tmp.unlink()

    @pytest.mark.asyncio
    async def test_default_action_is_list(self):
        tmp = _tmp_shortcuts_file([SAMPLE_SHORTCUT])
        with patch("mcp.handlers.shortcuts.SHORTCUTS_FILE", tmp):
            result = await handle_shortcut_manage({})
        assert result["ok"] is True
        assert "shortcuts" in result
        tmp.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
