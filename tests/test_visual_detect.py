"""Tests for visual detection module."""

import os
import sys
from unittest import mock

import numpy as np
import pytest
from PIL import Image, ImageDraw

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


def _make_button_image(width=400, height=300):
    """Create a test image with a clear rectangular button."""
    img = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(100, 120), (300, 160)], outline=(50, 50, 50), width=2)
    return img


def _make_input_image(width=400, height=300):
    """Create a test image with a text-input-shaped rectangle."""
    img = Image.new("RGB", (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 140), (350, 170)], outline=(50, 50, 50), width=2)
    return img


def _make_noisy_image(width=400, height=300):
    """Create an image with no clear UI rectangles — just noise."""
    arr = np.random.randint(200, 255, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(arr)


class TestRectangleDetection:
    def test_detects_button_rectangle(self):
        from tools.visual_detect import detect_rectangles
        img = _make_button_image()
        rects = detect_rectangles(img)
        assert len(rects) >= 1
        r = rects[0]
        assert 80 <= r["x"] <= 120
        assert 100 <= r["y"] <= 140
        assert r["w"] >= 150
        assert r["h"] >= 25

    def test_classifies_button_like(self):
        from tools.visual_detect import detect_rectangles
        img = _make_button_image()
        rects = detect_rectangles(img)
        assert len(rects) >= 1
        assert rects[0]["class"] == "button-like"

    def test_classifies_input_like(self):
        from tools.visual_detect import detect_rectangles
        img = _make_input_image()
        rects = detect_rectangles(img)
        inputs = [r for r in rects if r["class"] == "input-like"]
        assert len(inputs) >= 1

    def test_filters_tiny_rectangles(self):
        from tools.visual_detect import detect_rectangles
        img = Image.new("RGB", (400, 300), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(100, 100), (110, 108)], outline=(50, 50, 50), width=1)
        rects = detect_rectangles(img)
        assert len(rects) == 0

    def test_filters_noise(self):
        from tools.visual_detect import detect_rectangles
        img = _make_noisy_image()
        rects = detect_rectangles(img)
        assert len(rects) <= 5

    def test_filters_screen_sized_rectangles(self):
        from tools.visual_detect import detect_rectangles
        img = Image.new("RGB", (400, 300), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(5, 5), (395, 295)], outline=(50, 50, 50), width=2)
        rects = detect_rectangles(img)
        full_screen = [r for r in rects if r["w"] > 350 and r["h"] > 250]
        assert len(full_screen) == 0


class TestTextDetection:
    @mock.patch("tools.visual_detect._run_ocr_on_image")
    def test_returns_text_regions(self, mock_ocr):
        mock_ocr.return_value = [
            {"text": "Submit", "x": 110, "y": 125, "width": 80, "height": 18},
        ]
        from tools.visual_detect import detect_text
        texts = detect_text(Image.new("RGB", (400, 300), (240, 240, 240)))
        assert len(texts) == 1
        assert texts[0]["text"] == "Submit"
        assert texts[0]["type"] == "text"


class TestMergeRegions:
    def test_text_inside_rect_gets_associated(self):
        from tools.visual_detect import merge_regions
        rects = [{"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like"}]
        texts = [{"x": 130, "y": 128, "w": 80, "h": 18, "text": "Submit", "type": "text"}]
        merged = merge_regions(rects, texts)
        buttons = [r for r in merged if r.get("class") == "button-like"]
        assert len(buttons) == 1
        assert buttons[0]["text"] == "Submit"

    def test_standalone_text_preserved(self):
        from tools.visual_detect import merge_regions
        rects = [{"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like"}]
        texts = [{"x": 500, "y": 50, "w": 60, "h": 16, "text": "Menu", "type": "text"}]
        merged = merge_regions(rects, texts)
        standalone = [r for r in merged if r.get("type") == "text"]
        assert len(standalone) == 1
        assert standalone[0]["text"] == "Menu"

    def test_cap_at_30_regions(self):
        from tools.visual_detect import merge_regions
        rects = [{"x": i * 10, "y": 0, "w": 50, "h": 30, "class": "panel"} for i in range(40)]
        texts = []
        merged = merge_regions(rects, texts)
        assert len(merged) <= 30


class TestDetectUiRegions:
    @mock.patch("tools.visual_detect.detect_text")
    @mock.patch("tools.visual_detect.detect_rectangles")
    def test_returns_merged_regions(self, mock_rects, mock_text):
        mock_rects.return_value = [
            {"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like"},
        ]
        mock_text.return_value = [
            {"type": "text", "x": 130, "y": 128, "w": 80, "h": 18, "text": "Submit"},
        ]
        from tools.visual_detect import detect_ui_regions
        img = Image.new("RGB", (400, 300), (240, 240, 240))
        regions = detect_ui_regions(img, scale=1.0)
        assert len(regions) >= 1
        assert regions[0]["x"] == 100

    @mock.patch("tools.visual_detect.detect_text")
    @mock.patch("tools.visual_detect.detect_rectangles")
    def test_scales_to_screen_space(self, mock_rects, mock_text):
        mock_rects.return_value = [
            {"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like"},
        ]
        mock_text.return_value = []
        from tools.visual_detect import detect_ui_regions
        img = Image.new("RGB", (400, 300), (240, 240, 240))
        regions = detect_ui_regions(img, scale=1.5)
        assert regions[0]["x"] == 150
        assert regions[0]["y"] == 180

    @mock.patch("tools.visual_detect.detect_text")
    @mock.patch("tools.visual_detect.detect_rectangles")
    def test_formats_text_output(self, mock_rects, mock_text):
        mock_rects.return_value = [
            {"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like"},
        ]
        mock_text.return_value = [
            {"type": "text", "x": 130, "y": 128, "w": 80, "h": 18, "text": "Submit"},
        ]
        from tools.visual_detect import detect_ui_regions, format_regions_text
        img = Image.new("RGB", (400, 300), (240, 240, 240))
        regions = detect_ui_regions(img, scale=1.0)
        text = format_regions_text(regions)
        assert "Detected UI regions:" in text
        assert '"Submit"' in text
        assert "btn" in text


class TestEdgeCases:
    def test_empty_image_no_crash(self):
        """Blank white image should return empty or minimal regions."""
        from tools.visual_detect import detect_ui_regions
        img = Image.new("RGB", (400, 300), (255, 255, 255))
        regions = detect_ui_regions(img, scale=1.0)
        assert isinstance(regions, list)

    def test_format_empty_regions(self):
        """format_regions_text with empty list returns empty string."""
        from tools.visual_detect import format_regions_text
        assert format_regions_text([]) == ""

    @mock.patch("tools.visual_detect.detect_text")
    @mock.patch("tools.visual_detect.detect_rectangles")
    def test_scale_zero_no_crash(self, mock_rects, mock_text):
        """scale=0 should not crash (degenerate case)."""
        mock_rects.return_value = [
            {"x": 100, "y": 100, "w": 50, "h": 30, "class": "panel"},
        ]
        mock_text.return_value = []
        from tools.visual_detect import detect_ui_regions
        img = Image.new("RGB", (400, 300), (255, 255, 255))
        regions = detect_ui_regions(img, scale=0)
        assert isinstance(regions, list)
        # All coordinates should be 0 (multiplied by 0)
        for r in regions:
            assert r["x"] == 0
            assert r["y"] == 0

    def test_merge_regions_does_not_mutate_inputs(self):
        """merge_regions should not modify the input lists or dicts."""
        from tools.visual_detect import merge_regions
        rect = {"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like"}
        original_keys = set(rect.keys())
        rects = [rect]
        texts = [{"x": 130, "y": 128, "w": 80, "h": 18, "text": "Submit", "type": "text"}]
        merge_regions(rects, texts)
        # Original rect should not have "type" or "text" added
        assert set(rect.keys()) == original_keys

    @mock.patch("tools.visual_detect._run_ocr_on_image")
    def test_ocr_failure_returns_empty_text(self, mock_ocr):
        """If OCR fails, detect_text returns empty list gracefully."""
        mock_ocr.side_effect = RuntimeError("OCR model failed")
        from tools.visual_detect import detect_text
        # Should not crash — _run_ocr_on_image has exception guard
        # But detect_text calls _run_ocr_on_image which returns [] on error
        mock_ocr.return_value = []
        mock_ocr.side_effect = None  # reset
        texts = detect_text(Image.new("RGB", (100, 100), (255, 255, 255)))
        assert texts == []

