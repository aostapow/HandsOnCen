"""Tests for the manage tools (clipboard, manage_screenshots).

Validates helper/validation functions, core function behaviour with mocked
pyperclip and screenshot_manager, and MCP tool registration.
"""

import os
import sys
from unittest import mock

import pytest

# Make the handson-server package importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


# ---------------------------------------------------------------------------
# Test: validate_screenshot_action
# ---------------------------------------------------------------------------

class TestScreenshotActionValidation:
    def test_valid_screenshot_actions(self):
        from tools.manage import validate_screenshot_action
        for action in ("list", "cleanup", "set_limit"):
            assert validate_screenshot_action(action) == action

    def test_invalid_screenshot_action(self):
        from tools.manage import validate_screenshot_action
        with pytest.raises(ValueError, match="Invalid action"):
            validate_screenshot_action("delete_all_files")

    def test_case_insensitive(self):
        from tools.manage import validate_screenshot_action
        assert validate_screenshot_action("LIST") == "list"
        assert validate_screenshot_action("Cleanup") == "cleanup"
        assert validate_screenshot_action("SET_LIMIT") == "set_limit"

    def test_empty_string_raises(self):
        from tools.manage import validate_screenshot_action
        with pytest.raises(ValueError):
            validate_screenshot_action("")


# ---------------------------------------------------------------------------
# Test: validate_clipboard_action
# ---------------------------------------------------------------------------

class TestClipboardActionValidation:
    def test_valid_clipboard_actions(self):
        from tools.manage import validate_clipboard_action
        for action in ("read", "write"):
            assert validate_clipboard_action(action) == action

    def test_invalid_clipboard_action(self):
        from tools.manage import validate_clipboard_action
        with pytest.raises(ValueError, match="Invalid action"):
            validate_clipboard_action("execute")

    def test_case_insensitive(self):
        from tools.manage import validate_clipboard_action
        assert validate_clipboard_action("READ") == "read"
        assert validate_clipboard_action("Write") == "write"

    def test_empty_string_raises(self):
        from tools.manage import validate_clipboard_action
        with pytest.raises(ValueError):
            validate_clipboard_action("")


# ---------------------------------------------------------------------------
# Test: do_clipboard_read (mocked pyperclip)
# ---------------------------------------------------------------------------

class TestDoClipboardRead:
    @mock.patch("tools.manage.pyperclip")
    def test_returns_clipboard_content(self, mock_pyperclip):
        from tools.manage import do_clipboard_read
        mock_pyperclip.paste.return_value = "hello from clipboard"
        result = do_clipboard_read()
        mock_pyperclip.paste.assert_called_once()
        assert result == "hello from clipboard"

    @mock.patch("tools.manage.pyperclip")
    def test_returns_empty_string(self, mock_pyperclip):
        from tools.manage import do_clipboard_read
        mock_pyperclip.paste.return_value = ""
        result = do_clipboard_read()
        assert result == ""


# ---------------------------------------------------------------------------
# Test: do_clipboard_write (mocked pyperclip)
# ---------------------------------------------------------------------------

class TestDoClipboardWrite:
    @mock.patch("tools.manage.pyperclip")
    def test_writes_text_to_clipboard(self, mock_pyperclip):
        from tools.manage import do_clipboard_write
        do_clipboard_write("some text")
        mock_pyperclip.copy.assert_called_once_with("some text")

    @mock.patch("tools.manage.pyperclip")
    def test_writes_empty_string(self, mock_pyperclip):
        from tools.manage import do_clipboard_write
        do_clipboard_write("")
        mock_pyperclip.copy.assert_called_once_with("")

    @mock.patch("tools.manage.pyperclip")
    def test_writes_multiline_text(self, mock_pyperclip):
        from tools.manage import do_clipboard_write
        text = "line 1\nline 2\nline 3"
        do_clipboard_write(text)
        mock_pyperclip.copy.assert_called_once_with(text)


# ---------------------------------------------------------------------------
# Test: register (tool count)
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_returns_two(self):
        from tools.manage import register
        mock_server = mock.MagicMock()
        # server.tool() returns a decorator, which returns the function
        mock_server.tool.return_value = lambda fn: fn
        count = register(mock_server)
        assert count == 2
        assert mock_server.tool.call_count == 2

