# tests/test_dpi.py
"""Tests for DPI scaling functions."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestDpiDetection:
    def setup_method(self):
        import tools.screenshot
        tools.screenshot._dpi_scale = None

    @mock.patch("tools.screenshot._query_dpi", return_value=1.5)
    def test_get_dpi_scale(self, mock_query):
        from tools.screenshot import get_dpi_scale
        assert get_dpi_scale() == 1.5

    @mock.patch("tools.screenshot._query_dpi", return_value=1.0)
    def test_dpi_100_percent(self, mock_query):
        from tools.screenshot import get_dpi_scale
        assert get_dpi_scale() == 1.0


class TestCoordinateConversion:
    def test_physical_to_logical_at_150(self):
        from tools.screenshot import physical_to_logical
        x, y = physical_to_logical(300, 450, scale=1.5)
        assert x == 200
        assert y == 300

    def test_logical_to_physical_at_150(self):
        from tools.screenshot import logical_to_physical
        x, y = logical_to_physical(200, 300, scale=1.5)
        assert x == 300
        assert y == 450

    def test_noop_at_100(self):
        from tools.screenshot import physical_to_logical, logical_to_physical
        assert physical_to_logical(500, 500, scale=1.0) == (500, 500)
        assert logical_to_physical(500, 500, scale=1.0) == (500, 500)


class TestDarwinDpi:
    """macOS-specific DPI tests."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_retina_scale_factor(self):
        """On macOS, scale should be 1.0 or 2.0."""
        from handson_platform import get_dpi_scale as plat_dpi
        scale = plat_dpi()
        assert scale in (1.0, 2.0), f"Unexpected scale: {scale}"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_screenshot_dpi_uses_platform(self):
        """tools/screenshot.py should use handson_platform for DPI."""
        import tools.screenshot
        tools.screenshot._dpi_scale = None  # reset cache
        scale = tools.screenshot.get_dpi_scale()
        assert isinstance(scale, float)
        assert scale >= 1.0

