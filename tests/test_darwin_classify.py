"""macOS-specific tests for window type classification."""

import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestDarwinClassifyPatterns:
    """Test classification logic with mocked app data."""

    def test_terminal_detected(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.apple.Terminal", "Terminal")
        assert result == "terminal"

    def test_iterm_detected(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.googlecode.iterm2", "iTerm2")
        assert result == "terminal"

    def test_chrome_detected(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.google.Chrome", "Google Chrome")
        assert result == "browser"

    def test_safari_detected(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.apple.Safari", "Safari")
        assert result == "browser"

    def test_vscode_detected_as_electron(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.microsoft.VSCode", "Visual Studio Code")
        assert result == "electron"

    def test_unknown_app(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.random.app", "Random App")
        assert result == "generic"

    def test_electron_in_process_name(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.unknown.app", "Electron Helper")
        assert result == "electron"

    def test_ghostty_detected(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("com.mitchellh.ghostty", "Ghostty")
        assert result == "terminal"

    def test_arc_detected(self):
        from handson_platform.darwin_backend import _classify_by_bundle
        result = _classify_by_bundle("company.thebrowser.Browser", "Arc")
        assert result == "browser"


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestClassifyWindowNative:
    """Test classify_window_native returns expected structure."""

    def test_returns_dict_with_required_keys(self):
        from handson_platform import classify_window_native
        result = classify_window_native()
        assert isinstance(result, dict)
        assert "type" in result
        assert "process_name" in result
        assert "pid" in result
        assert result["type"] in ("terminal", "browser", "electron", "generic")

