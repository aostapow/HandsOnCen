# tests/test_window_classify.py
"""Tests for window type classification."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestClassifyWindow:
    """Test _classify_hwnd with mocked Win32 calls."""

    def setup_method(self):
        from tools.window_classify import invalidate_cache
        invalidate_cache()

    @mock.patch("tools.window_classify._get_process_name", return_value="cmd.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="ConsoleWindowClass")
    def test_classic_console(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["type"] == "console"
        assert result["hwnd"] == 12345

    @mock.patch("tools.window_classify._get_process_name", return_value="WindowsTerminal.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="CASCADIA_HOSTING_WINDOW_CLASS")
    def test_windows_terminal(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["type"] == "terminal"

    @mock.patch("tools.window_classify._get_process_name", return_value="msedge.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="Chrome_WidgetWin_1")
    def test_browser_edge(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["type"] == "browser"

    @mock.patch("tools.window_classify._get_process_name", return_value="chrome.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="Chrome_WidgetWin_1")
    def test_browser_chrome(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["type"] == "browser"

    @mock.patch("tools.window_classify._get_process_name", return_value="Code.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="Chrome_WidgetWin_1")
    def test_electron_vscode(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["type"] == "electron"

    @mock.patch("tools.window_classify._get_process_name", return_value="notepad.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="Notepad")
    def test_generic_app(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["type"] == "generic"

    @mock.patch("tools.window_classify._get_process_name", return_value="powershell.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="ConsoleWindowClass")
    def test_returns_full_info(self, mock_class, mock_proc):
        from tools.window_classify import classify_window
        result = classify_window(12345)
        assert result["hwnd"] == 12345
        assert result["process_name"] == "powershell.exe"
        assert result["class_name"] == "ConsoleWindowClass"
        assert "pid" in result
        assert "is_elevated" in result


class TestCache:
    """Test that classification results are cached."""

    @mock.patch("tools.window_classify._get_process_name", return_value="notepad.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="Notepad")
    def test_cached_result(self, mock_class, mock_proc):
        from tools.window_classify import classify_window, invalidate_cache
        invalidate_cache()
        result1 = classify_window(99999)
        result2 = classify_window(99999)
        assert result1 == result2
        # _get_class_name called only once due to cache
        assert mock_class.call_count == 1

    @mock.patch("tools.window_classify._get_process_name", return_value="notepad.exe")
    @mock.patch("tools.window_classify._get_class_name", return_value="Notepad")
    def test_invalidate_clears_cache(self, mock_class, mock_proc):
        from tools.window_classify import classify_window, invalidate_cache
        invalidate_cache()
        classify_window(99999)
        invalidate_cache()
        classify_window(99999)
        assert mock_class.call_count == 2


class TestGetForegroundType:
    """Test get_foreground_type convenience function."""

    @mock.patch("tools.window_classify.classify_window")
    @mock.patch("tools.window_classify._get_foreground_hwnd", return_value=12345)
    def test_returns_classification(self, mock_fg, mock_classify):
        mock_classify.return_value = {"type": "browser", "hwnd": 12345}
        from tools.window_classify import get_foreground_type
        result = get_foreground_type()
        assert result["type"] == "browser"
        mock_classify.assert_called_once_with(12345)
