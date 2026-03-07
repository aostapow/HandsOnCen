"""Smoke tests for HandsOn on macOS -- verify core tools work end-to-end."""

import os
import sys

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestDarwinSmoke:
    """End-to-end smoke tests for macOS platform integration."""

    def test_platform_package_imports(self):
        """handson_platform should import cleanly on macOS."""
        import handson_platform
        assert hasattr(handson_platform, "get_dpi_scale")
        assert hasattr(handson_platform, "list_windows_native")
        assert hasattr(handson_platform, "classify_window_native")
        assert hasattr(handson_platform, "run_ocr_native")

    def test_dpi_scale_is_reasonable(self):
        """DPI scale should be 1.0 or 2.0 on macOS."""
        from handson_platform import get_dpi_scale
        scale = get_dpi_scale()
        assert isinstance(scale, float)
        assert 1.0 <= scale <= 3.0

    def test_list_windows_returns_data(self):
        """list_windows should return at least one window on a running macOS."""
        from handson_platform import list_windows_native
        windows = list_windows_native()
        assert isinstance(windows, list)
        # On a graphical macOS session, there should be at least one window
        assert len(windows) > 0
        # Verify structure
        w = windows[0]
        assert "title" in w
        assert "process_name" in w
        assert "x" in w
        assert "y" in w
        assert "width" in w
        assert "height" in w

    def test_get_foreground_title_returns_string(self):
        """get_foreground_title should return a non-empty string."""
        from handson_platform import get_foreground_title
        title = get_foreground_title()
        assert isinstance(title, str)

    def test_classify_window_returns_valid_type(self):
        """classify_window_native should return a dict with valid type."""
        from handson_platform import classify_window_native
        result = classify_window_native()
        assert isinstance(result, dict)
        assert result["type"] in ("terminal", "browser", "electron", "generic")
        assert "process_name" in result
        assert "pid" in result

    def test_is_elevated_returns_false(self):
        """Normally tests don't run as root."""
        from handson_platform import is_elevated
        assert is_elevated() is False

    def test_window_classify_get_foreground_type(self):
        """tools.window_classify.get_foreground_type should work on macOS."""
        from tools.window_classify import get_foreground_type
        result = get_foreground_type()
        assert isinstance(result, dict)
        assert "type" in result

    def test_framework_detect_on_macos(self):
        """tools.framework_detect.do_detect_framework should work on macOS."""
        from tools.framework_detect import do_detect_framework
        result = do_detect_framework()
        assert isinstance(result, dict)
        assert "framework" in result
        assert "uia_support" in result
        assert "hints" in result

    def test_input_tools_importable(self):
        """tools.input_tools should import without error on macOS."""
        import tools.input_tools
        assert hasattr(tools.input_tools, "do_type_text")
        assert hasattr(tools.input_tools, "do_send_keys")

    def test_screenshot_module_importable(self):
        """tools.screenshot should import and basic functions work."""
        from tools.screenshot import get_screen_size, get_dpi_scale
        monitors = get_screen_size()
        assert len(monitors) >= 2  # combined + at least 1 monitor
        scale = get_dpi_scale()
        assert isinstance(scale, float)
        assert 1.0 <= scale <= 3.0

