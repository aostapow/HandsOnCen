"""macOS framework detection tests."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestDarwinFrameworkDetection:
    """Test detect_framework_darwin with mocked app data."""

    def test_safari_is_cocoa(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.apple.Safari", "process_name": "Safari", "pid": 123}
            result = detect_framework_darwin("Safari")
            assert result["framework"] == "cocoa"
            assert result["uia_support"] == "full"

    def test_finder_is_cocoa(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.apple.finder", "process_name": "Finder", "pid": 100}
            result = detect_framework_darwin("Finder")
            assert result["framework"] == "cocoa"

    def test_apple_prefix_is_cocoa(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.apple.SomeNewApp", "process_name": "SomeNewApp", "pid": 200}
            result = detect_framework_darwin("SomeNewApp")
            assert result["framework"] == "cocoa"

    def test_chrome_is_browser(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.google.Chrome", "process_name": "Google Chrome", "pid": 456}
            result = detect_framework_darwin("Chrome")
            assert result["framework"] == "chromium_browser"

    def test_vscode_is_electron(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.microsoft.VSCode", "process_name": "Electron", "pid": 789}
            result = detect_framework_darwin("Code")
            assert result["framework"] == "electron"

    def test_iterm_is_terminal(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.googlecode.iterm2", "process_name": "iTerm2", "pid": 300}
            result = detect_framework_darwin("iTerm")
            assert result["framework"] == "terminal"

    def test_jetbrains_is_java(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.jetbrains.intellij", "process_name": "IntelliJ IDEA", "pid": 400}
            result = detect_framework_darwin("IntelliJ")
            assert result["framework"] == "java"

    def test_unknown_bundle(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.random.thing", "process_name": "Random", "pid": 999}
            result = detect_framework_darwin("Random")
            assert result["framework"] == "unknown"
            assert "hints" in result

    def test_no_window_found(self):
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = None
            result = detect_framework_darwin("NonExistent")
            assert result["framework"] == "unknown"
            assert result["process_name"] == ""

    def test_return_format_matches_windows(self):
        """Ensure the return dict has the same keys as the Windows version."""
        from handson_platform.darwin_backend import detect_framework_darwin
        with mock.patch("handson_platform.darwin_backend._get_app_info_for_title") as m:
            m.return_value = {"bundle_id": "com.apple.Safari", "process_name": "Safari", "pid": 123}
            result = detect_framework_darwin("Safari")
            assert "framework" in result
            assert "uia_support" in result
            assert "hints" in result
            assert "process_name" in result
            assert "class_name" in result
            assert isinstance(result["hints"], list)
