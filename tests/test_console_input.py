# tests/test_console_input.py
"""Tests for Win32 console input routing."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestConsoleTextInput:
    """Test _send_text_to_console with mocked Win32 APIs."""

    @mock.patch("tools.input_tools.ctypes")
    def test_attach_write_free_sequence(self, mock_ctypes):
        """Verify AttachConsole -> WriteConsoleInputW -> FreeConsole sequence."""
        from tools.input_tools import _send_text_to_console
        mock_ctypes.windll.kernel32.AttachConsole.return_value = True
        mock_ctypes.windll.kernel32.GetStdHandle.return_value = 42
        mock_ctypes.windll.kernel32.WriteConsoleInputW.return_value = True

        result = _send_text_to_console(100, "hello")

        mock_ctypes.windll.kernel32.AttachConsole.assert_called_once_with(100)
        # FreeConsole called twice: once before AttachConsole, once in finally
        assert mock_ctypes.windll.kernel32.FreeConsole.call_count == 2
        assert result["success"] is True

    @mock.patch("tools.input_tools.ctypes")
    def test_attach_fails_falls_back_to_sendmessage(self, mock_ctypes):
        """When AttachConsole fails, fall back to SendMessage(WM_CHAR)."""
        from tools.input_tools import _send_text_to_console
        mock_ctypes.windll.kernel32.AttachConsole.return_value = False
        mock_ctypes.windll.user32.SendMessageW.return_value = 0

        result = _send_text_to_console(100, "hi", hwnd=555)

        assert mock_ctypes.windll.user32.SendMessageW.call_count == 2  # 'h' + 'i'
        assert result["success"] is True
        assert result["method"] == "SendMessage"


class TestSmartRouting:
    """Test that do_type_text routes to console API when foreground is a console."""

    @mock.patch("tools.input_tools._send_text_to_console")
    @mock.patch("tools.input_tools.get_foreground_type")
    def test_routes_to_console_api(self, mock_fg, mock_send):
        mock_fg.return_value = {"type": "console", "pid": 100, "hwnd": 555, "is_elevated": False}
        mock_send.return_value = {"success": True, "method": "WriteConsoleInput"}

        from tools.input_tools import do_type_text
        result = do_type_text("hello")

        mock_send.assert_called_once()
        assert result["action"] == "type_text"

    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.input_tools.get_foreground_type")
    def test_routes_to_pyautogui_for_generic(self, mock_fg, mock_pag):
        mock_fg.return_value = {"type": "generic", "pid": 200, "hwnd": 666, "is_elevated": False}

        from tools.input_tools import do_type_text
        result = do_type_text("hello")

        mock_pag.write.assert_called_once()


class TestConsoleKeyInput:
    """Test _send_keys_to_console for special keys."""

    @mock.patch("tools.input_tools.ctypes")
    def test_sends_enter_key(self, mock_ctypes):
        from tools.input_tools import _send_keys_to_console
        mock_ctypes.windll.kernel32.AttachConsole.return_value = True
        mock_ctypes.windll.kernel32.GetStdHandle.return_value = 42
        mock_ctypes.windll.kernel32.WriteConsoleInputW.return_value = True

        result = _send_keys_to_console(100, "enter")
        assert result["success"] is True

