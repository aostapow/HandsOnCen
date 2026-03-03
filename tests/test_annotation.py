# tests/test_annotation.py
"""Tests for screenshot annotation."""

import os
import sys
from unittest import mock

import pytest
from PIL import Image

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestAnnotateScreenshot:
    def test_grid_draws_lines(self):
        from tools.screenshot import annotate_image
        img = Image.new("RGB", (1500, 1000), "black")
        annotated = annotate_image(img, grid=True, mouse_pos=None, elements=None)
        # Image should be same size
        assert annotated.size == (1500, 1000)
        # Should have changed some pixels (grid lines are not black)
        assert annotated != img  # Different object

    def test_mouse_crosshair(self):
        from tools.screenshot import annotate_image
        img = Image.new("RGB", (800, 600), "black")
        annotated = annotate_image(img, grid=False, mouse_pos=(400, 300), elements=None)
        assert annotated.size == (800, 600)

    def test_element_outlines(self):
        from tools.screenshot import annotate_image
        img = Image.new("RGB", (800, 600), "white")
        elements = [
            {"name": "OK", "role": "Button", "x": 100, "y": 200, "width": 80, "height": 30},
        ]
        annotated = annotate_image(img, grid=False, mouse_pos=None, elements=elements)
        assert annotated.size == (800, 600)

    def test_returns_new_image(self):
        """Annotation should not modify original image."""
        from tools.screenshot import annotate_image
        img = Image.new("RGB", (400, 300), "black")
        original_data = list(img.getdata())
        annotate_image(img, grid=True, mouse_pos=(200, 150), elements=None)
        assert list(img.getdata()) == original_data
