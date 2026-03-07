"""macOS Vision framework OCR tests."""

import os
import sys
import tempfile

import pytest
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


def _create_test_image_with_text(text="Hello World", size=(400, 100)):
    """Create a test image with rendered text."""
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text((20, 30), text, fill="black", font=font)
    return img


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestVisionOCR:
    def test_finds_text_in_image(self):
        from handson_platform import run_ocr_native

        img = _create_test_image_with_text("Hello World")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, format="PNG")
            path = f.name

        try:
            words = run_ocr_native(path)
            assert isinstance(words, list)
            assert len(words) > 0
            texts = [w["text"].lower() for w in words]
            assert any("hello" in t for t in texts)
        finally:
            os.unlink(path)

    def test_returns_word_dicts_with_coordinates(self):
        from handson_platform import run_ocr_native

        img = _create_test_image_with_text("Test Button")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, format="PNG")
            path = f.name

        try:
            words = run_ocr_native(path)
            if words:
                w = words[0]
                assert "text" in w
                assert "x" in w
                assert "y" in w
                assert "width" in w
                assert "height" in w
                assert isinstance(w["x"], int)
                assert isinstance(w["y"], int)
        finally:
            os.unlink(path)

    def test_empty_image_returns_list(self):
        from handson_platform import run_ocr_native

        img = Image.new("RGB", (200, 200), "white")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, format="PNG")
            path = f.name

        try:
            words = run_ocr_native(path)
            assert isinstance(words, list)
        finally:
            os.unlink(path)

    def test_ocr_engine_dispatches_to_vision(self):
        """When RapidOCR is not available, _run_ocr_engine should use Vision on macOS."""
        from unittest import mock
        from tools.ocr import _run_ocr_engine

        img = _create_test_image_with_text("Dispatch Test")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f, format="PNG")
            path = f.name

        try:
            with mock.patch("tools.ocr._get_rapid_engine", return_value=None):
                words = _run_ocr_engine(path)
                assert isinstance(words, list)
        finally:
            os.unlink(path)

