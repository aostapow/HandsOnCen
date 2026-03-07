# tests/test_framework_detect.py
"""Tests for UI framework detection."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestDetectFramework:
    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_qt(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "python.exe"
        mock_class.return_value = "Qt681QWindowIcon"
        mock_dlls.return_value = ["Qt6Core.dll", "Qt6Gui.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "qt"
        assert result["uia_support"] == "partial"
        assert any("custom" in h.lower() or "qwidget" in h.lower() for h in result["hints"])

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_electron(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "Code.exe"
        mock_class.return_value = "Chrome_WidgetWin_1"
        mock_dlls.return_value = ["chrome_elf.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "electron"
        assert result["uia_support"] == "conditional"
        assert any("accessibility" in h.lower() for h in result["hints"])

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_wpf(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "MyApp.exe"
        mock_class.return_value = "HwndWrapper[MyApp.exe;;abcd1234]"
        mock_dlls.return_value = ["wpfgfx_cor3.dll", "PresentationCore.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "wpf"
        assert result["uia_support"] == "full"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_winforms(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "MyLegacyApp.exe"
        mock_class.return_value = "WindowsForms10.Window.8.app.0.2bf8098_r11_ad1"
        mock_dlls.return_value = ["mscoree.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "winforms"
        assert result["uia_support"] == "partial"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_java_swing(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "javaw.exe"
        mock_class.return_value = "SunAwtFrame"
        mock_dlls.return_value = ["jvm.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "java_swing"
        assert result["uia_support"] == "conditional"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_gtk(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "gimp.exe"
        mock_class.return_value = "gdkWindowToplevel"
        mock_dlls.return_value = ["libgtk-3-0.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "gtk"
        assert result["uia_support"] == "none"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_chrome_not_detected_as_electron(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        """Chrome browser should be 'chromium_browser', not 'electron'."""
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "chrome.exe"
        mock_class.return_value = "Chrome_WidgetWin_1"
        mock_dlls.return_value = []

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "chromium_browser"
        assert result["uia_support"] == "conditional"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_edge_not_detected_as_electron(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        """Edge browser should be 'chromium_browser', not 'electron'."""
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "msedge.exe"
        mock_class.return_value = "Chrome_WidgetWin_1"
        mock_dlls.return_value = []

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "chromium_browser"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_electron_app_still_detected(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        """Non-browser Electron apps (like VS Code) should still be 'electron'."""
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "Code.exe"
        mock_class.return_value = "Chrome_WidgetWin_1"
        mock_dlls.return_value = []

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "electron"
        assert result["uia_support"] == "conditional"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_detects_uwp(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        """UWP apps with ApplicationFrameWindow should be detected."""
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "SystemSettings.exe"
        mock_class.return_value = "ApplicationFrameWindow"
        mock_dlls.return_value = []

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "uwp"
        assert result["uia_support"] == "full"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_unknown_framework(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "mystery.exe"
        mock_class.return_value = "SomeUnknownClass"
        mock_dlls.return_value = []

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "unknown"

    @mock.patch("tools.framework_detect._get_loaded_dlls")
    @mock.patch("tools.framework_detect._get_class_name")
    @mock.patch("tools.framework_detect._get_process_name")
    @mock.patch("tools.framework_detect._get_hwnd_for_window")
    def test_win32_native(self, mock_hwnd, mock_proc, mock_class, mock_dlls):
        mock_hwnd.return_value = 12345
        mock_proc.return_value = "notepad.exe"
        mock_class.return_value = "Notepad"
        mock_dlls.return_value = ["comctl32.dll"]

        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()

        assert result["framework"] == "win32"
        assert result["uia_support"] == "partial"


class TestRegister:
    def test_registers_one_tool(self):
        server = mock.MagicMock()
        from tools.framework_detect import register
        count = register(server)
        assert count == 1

