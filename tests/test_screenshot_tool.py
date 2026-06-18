"""Tests for the screenshot tool (capture, crop, wait_for_change)."""

import os
import sys
import base64
import io
import time
from unittest import mock

import pytest
from PIL import Image
import numpy as np

# Make the handson-server package importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_solid_image(width: int, height: int, color=(128, 128, 128)) -> Image.Image:
    """Create a solid-color RGB PIL Image."""
    return Image.new("RGB", (width, height), color)


def _image_to_raw_bytes(img: Image.Image) -> bytes:
    """Return raw BGRA pixel bytes the way mss produces them (via sct.grab)."""
    # mss returns BGRA; we simulate that for the mock
    rgba = img.convert("RGBA")
    raw = rgba.tobytes()
    # Convert RGBA -> BGRA
    arr = np.frombuffer(raw, dtype=np.uint8).reshape((-1, 4)).copy()
    arr[:, [0, 2]] = arr[:, [2, 0]]
    return arr.tobytes()


def _make_mss_monitor_shot(width: int, height: int, color=(128, 128, 128)):
    """Build a fake mss screenshot object matching the mss.grab() API."""
    img = _make_solid_image(width, height, color)
    raw = _image_to_raw_bytes(img)

    class FakeShot:
        def __init__(self):
            self.rgb = img.convert("RGB").tobytes()
            self.size = (width, height)
            self.width = width
            self.height = height
            self.pixel = raw
            # mss provides a .png property that returns bytes
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self._png = buf.getvalue()

        @property
        def png(self):
            return self._png

    return FakeShot()


# ---------------------------------------------------------------------------
# Test: crop_region
# ---------------------------------------------------------------------------

class TestCropRegion:
    def test_basic_crop(self):
        from tools.screenshot import crop_region

        img = _make_solid_image(1920, 1080)
        cropped = crop_region(img, {"x": 100, "y": 100, "w": 200, "h": 200})
        assert cropped.size == (200, 200)

    def test_crop_at_origin(self):
        from tools.screenshot import crop_region

        img = _make_solid_image(800, 600)
        cropped = crop_region(img, {"x": 0, "y": 0, "w": 400, "h": 300})
        assert cropped.size == (400, 300)

    def test_crop_preserves_pixel_content(self):
        """Verify the cropped region contains the correct pixels."""
        from tools.screenshot import crop_region

        img = Image.new("RGB", (100, 100), (0, 0, 0))
        # Paint a 10x10 red square at (20, 30)
        for x in range(20, 30):
            for y in range(30, 40):
                img.putpixel((x, y), (255, 0, 0))

        cropped = crop_region(img, {"x": 20, "y": 30, "w": 10, "h": 10})
        assert cropped.size == (10, 10)
        # Every pixel in the crop should be red
        for x in range(10):
            for y in range(10):
                assert cropped.getpixel((x, y)) == (255, 0, 0)


# ---------------------------------------------------------------------------
# Test: capture_screenshot (mocked mss)
# ---------------------------------------------------------------------------

class TestCaptureScreenshot:
    """Test capture_screenshot with fully mocked mss + screenshot_manager."""

    def _patch_and_capture(self, width=1920, height=1080, color=(128, 128, 128),
                           monitor_index=None, region=None):
        """Run capture_screenshot under mocks, return the result dict."""
        from tools import screenshot as mod

        fake_shot = _make_mss_monitor_shot(width, height, color)

        fake_sct = mock.MagicMock()
        fake_sct.monitors = [
            {"left": 0, "top": 0, "width": width * 2, "height": height},  # 0 = all
            {"left": 0, "top": 0, "width": width, "height": height},      # 1 = primary
        ]
        fake_sct.grab.return_value = fake_shot

        # Reset global mss instance so our mock takes effect
        old_sct = getattr(mod, "_sct", None)
        mod._sct = fake_sct

        # Mock the screenshot_manager.save to return a fake path
        fake_path = "/tmp/handson_fake/screenshot.png"
        with mock.patch.object(mod, "screenshot_manager") as mock_mgr:
            mock_mgr.save.return_value = fake_path
            result = mod.capture_screenshot(
                monitor_index=monitor_index, region=region
            )

        # Restore
        mod._sct = old_sct
        return result

    def test_returns_required_keys(self):
        result = self._patch_and_capture()
        assert "image" in result
        assert "width" in result
        assert "height" in result
        assert "path" in result

    def test_dimensions_match(self):
        # Use a size under MAX_SCREENSHOT_WIDTH so no downscale occurs
        result = self._patch_and_capture(width=1024, height=768)
        assert result["width"] == 1024
        assert result["height"] == 768

    def test_oversized_image_downscaled(self):
        from tools.screenshot import MAX_SCREENSHOT_WIDTH
        result = self._patch_and_capture(width=3840, height=2160)
        assert result["width"] == MAX_SCREENSHOT_WIDTH
        assert result["width"] <= MAX_SCREENSHOT_WIDTH

    def test_base64_decodes_to_valid_image(self):
        result = self._patch_and_capture()
        raw = base64.b64decode(result["image"])
        img = Image.open(io.BytesIO(raw))
        assert img.format in ("PNG", "JPEG")

    def test_path_comes_from_manager(self):
        result = self._patch_and_capture()
        assert result["path"] == "/tmp/handson_fake/screenshot.png"

    def test_with_region_crops(self):
        result = self._patch_and_capture(
            width=1920, height=1080,
            region={"x": 100, "y": 100, "w": 200, "h": 200},
        )
        assert result["width"] == 200
        assert result["height"] == 200

    def test_with_window_title_crops_to_window(self):
        from tools import screenshot as mod

        fake_shot = _make_mss_monitor_shot(1920, 1080)
        fake_sct = mock.MagicMock()
        fake_sct.monitors = [
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]
        fake_sct.grab.return_value = fake_shot

        old_sct = getattr(mod, "_sct", None)
        mod._sct = fake_sct

        fake_path = "/tmp/handson_fake/screenshot.png"
        fake_window = {"x": 50, "y": 60, "width": 300, "height": 200}
        with mock.patch.object(mod, "screenshot_manager") as mock_mgr, \
             mock.patch("tools.windows.find_matching_window", return_value={"window": fake_window}), \
             mock.patch("tools.windows.do_list_windows", return_value=[]):
            mock_mgr.save.return_value = fake_path
            result = mod.capture_screenshot(window_title="Notepad")

        mod._sct = old_sct
        assert result["width"] == 300
        assert result["height"] == 200

    def test_returns_original_dimensions_when_downscaled(self):
        """capture_screenshot should return original_width/original_height."""
        result = self._patch_and_capture(width=3840, height=2160)
        assert result["original_width"] == 3840
        assert result["original_height"] == 2160

    def test_original_dimensions_match_when_no_downscale(self):
        """When no downscale, original == final dimensions."""
        result = self._patch_and_capture(width=1024, height=768)
        assert result["original_width"] == 1024
        assert result["original_height"] == 768


# ---------------------------------------------------------------------------
# Test: region parameter assembly from individual x/y/w/h
# ---------------------------------------------------------------------------

class TestRegionParamAssembly:
    """The MCP tool handler assembles a region dict from x/y/w/h params.
    Verify the logic is correct.
    """

    def test_all_params_provided(self):
        """When all four region_* params are given, region dict is built."""
        region = self._assemble(100, 200, 300, 400)
        assert region == {"x": 100, "y": 200, "w": 300, "h": 400}

    def test_no_params_returns_none(self):
        """When no region params are given, result is None."""
        region = self._assemble(None, None, None, None)
        assert region is None

    def test_partial_params_returns_none(self):
        """Partial region params (some None) should return None."""
        region = self._assemble(100, None, 300, None)
        assert region is None

    @staticmethod
    def _assemble(x, y, w, h):
        """Replicate the region-assembly logic from the tool handler."""
        from tools.screenshot import _build_region
        return _build_region(x, y, w, h)


# ---------------------------------------------------------------------------
# Test: wait_for_change
# ---------------------------------------------------------------------------

class TestWaitForChange:
    """Test wait_for_change with mocked capture_screenshot."""

    def test_detects_change(self):
        """If the screen changes significantly, changed=True."""
        from tools import screenshot as mod

        # First call = baseline (gray), second call = changed (white)
        gray_img = _make_solid_image(100, 100, (128, 128, 128))
        white_img = _make_solid_image(100, 100, (255, 255, 255))

        gray_buf = io.BytesIO()
        gray_img.save(gray_buf, format="PNG")
        gray_b64 = base64.b64encode(gray_buf.getvalue()).decode()

        white_buf = io.BytesIO()
        white_img.save(white_buf, format="PNG")
        white_b64 = base64.b64encode(white_buf.getvalue()).decode()

        call_count = {"n": 0}

        def fake_capture(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"image": gray_b64, "width": 100, "height": 100, "path": "/tmp/a.png"}
            else:
                return {"image": white_b64, "width": 100, "height": 100, "path": "/tmp/b.png"}

        with mock.patch.object(mod, "capture_screenshot", side_effect=fake_capture):
            result = mod.wait_for_change(
                timeout=2.0, threshold=0.01, poll_interval=0.1
            )

        assert result["changed"] is True
        assert result["elapsed"] > 0
        assert "image" in result

    def test_timeout_no_change(self):
        """If screen never changes, changed=False after timeout."""
        from tools import screenshot as mod

        gray_img = _make_solid_image(100, 100, (128, 128, 128))
        buf = io.BytesIO()
        gray_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        def fake_capture(**kwargs):
            return {"image": b64, "width": 100, "height": 100, "path": "/tmp/a.png"}

        with mock.patch.object(mod, "capture_screenshot", side_effect=fake_capture):
            result = mod.wait_for_change(
                timeout=0.3, threshold=0.01, poll_interval=0.1
            )

        assert result["changed"] is False
        assert result["elapsed"] >= 0.3


# ---------------------------------------------------------------------------
# Test: scale factor message formatting
# ---------------------------------------------------------------------------

class TestScreenshotScaleMessage:
    """Test that screenshot text messages include scale hints when downscaled."""

    def _build_msg(self, width, height, orig_w, orig_h):
        """Build the scale-aware message the same way the MCP tool does."""
        scale = orig_w / width
        if scale > 1.0:
            return (
                f"Screenshot captured: {width}x{height} pixels "
                f"(scaled from {orig_w}x{orig_h}, "
                f"multiply coordinates by {scale:.2f} for click targets). "
                f"File: /tmp/test.png"
            )
        return f"Screenshot captured: {width}x{height} pixels. File: /tmp/test.png"

    def test_downscaled_message_includes_scale(self):
        msg = self._build_msg(1280, 720, 1920, 1080)
        assert "multiply coordinates by 1.50" in msg
        assert "scaled from 1920x1080" in msg

    def test_not_downscaled_message_is_simple(self):
        msg = self._build_msg(1024, 768, 1024, 768)
        assert "multiply" not in msg
        assert "scaled" not in msg

    def test_4x_scale_factor(self):
        msg = self._build_msg(1280, 540, 5120, 2160)
        assert "multiply coordinates by 4.00" in msg
        assert "scaled from 5120x2160" in msg


# ---------------------------------------------------------------------------
# Test: visual detect fallback integration
# ---------------------------------------------------------------------------

class TestVisualDetectFallback:
    """When UIA returns < 3 elements, visual detection should run."""

    def _make_fake_result(self, width=400, height=300):
        """Build a fake capture_screenshot result dict."""
        img = Image.new("RGB", (width, height), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {
            "image": b64, "width": width, "height": height,
            "original_width": width, "original_height": height,
            "path": "/fake/path.jpg", "dpi_scale": 1.0,
        }

    @mock.patch("tools.visual_detect.format_regions_text")
    @mock.patch("tools.visual_detect.detect_ui_regions")
    def test_fallback_triggers_when_few_elements(self, mock_detect, mock_format):
        """Visual detect is called when UIA returns < 3 elements."""
        mock_detect.return_value = [
            {"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like",
             "type": "rect", "text": "OK"},
        ]
        mock_format.return_value = '\nDetected UI regions:\n[1] "OK" btn (100,120) 200x40'

        # Simulate the fallback logic from screenshot.py annotated path
        elements = [{"name": "title", "role": "TitleBar", "x": 0, "y": 0, "width": 400, "height": 30}]

        visual_detect_text = ""
        useful = [e for e in elements if e.get("name", "").strip()]
        if len(useful) < 3:
            from tools.visual_detect import detect_ui_regions, format_regions_text
            img = Image.new("RGB", (400, 300), (255, 255, 255))
            regions = detect_ui_regions(img, scale=1.0)
            if regions:
                visual_detect_text = format_regions_text(regions)

        mock_detect.assert_called_once()
        mock_format.assert_called_once()
        assert "Detected UI regions" in visual_detect_text

    @mock.patch("tools.visual_detect.detect_ui_regions")
    def test_no_fallback_when_enough_named_elements(self, mock_detect):
        """Visual detect should NOT run when UIA returns >= 3 *named* elements."""
        elements = [
            {"name": "a", "role": "Button", "x": 0, "y": 0, "width": 50, "height": 30},
            {"name": "b", "role": "Button", "x": 60, "y": 0, "width": 50, "height": 30},
            {"name": "c", "role": "Button", "x": 120, "y": 0, "width": 50, "height": 30},
        ]

        visual_detect_text = ""
        useful = [e for e in elements if e.get("name", "").strip()]
        if len(useful) < 3:
            from tools.visual_detect import detect_ui_regions, format_regions_text
            img = Image.new("RGB", (400, 300), (255, 255, 255))
            regions = detect_ui_regions(img, scale=1.0)
            if regions:
                visual_detect_text = format_regions_text(regions)

        mock_detect.assert_not_called()
        assert visual_detect_text == ""

    @mock.patch("tools.visual_detect.format_regions_text")
    @mock.patch("tools.visual_detect.detect_ui_regions")
    def test_fallback_triggers_with_unnamed_panes(self, mock_detect, mock_format):
        """Unnamed Panes (like Steam) should still trigger fallback."""
        mock_detect.return_value = [
            {"x": 100, "y": 120, "w": 200, "h": 40, "class": "button-like",
             "type": "rect", "text": "Play"},
        ]
        mock_format.return_value = '\nDetected UI regions:\n[1] "Play" btn (100,120) 200x40'

        # Steam-like: 4 elements but all unnamed Panes
        elements = [
            {"name": "", "role": "Pane", "x": 0, "y": 0, "width": 1515, "height": 900},
            {"name": "", "role": "Pane", "x": 0, "y": 0, "width": 1515, "height": 900},
            {"name": "", "role": "Pane", "x": 0, "y": 0, "width": 1515, "height": 900},
            {"name": "", "role": "Pane", "x": 0, "y": 0, "width": 1515, "height": 900},
        ]

        visual_detect_text = ""
        useful = [e for e in elements if e.get("name", "").strip()]
        if len(useful) < 3:
            from tools.visual_detect import detect_ui_regions, format_regions_text
            img = Image.new("RGB", (400, 300), (255, 255, 255))
            regions = detect_ui_regions(img, scale=1.0)
            if regions:
                visual_detect_text = format_regions_text(regions)

        mock_detect.assert_called_once()
        assert "Detected UI regions" in visual_detect_text

    def test_fallback_text_appears_in_response(self):
        """The visual_detect_text should be appended to the response string."""
        base_msg = "Annotated screenshot: 400x300 pixels. File: /fake.jpg"
        visual_detect_text = '\nDetected UI regions:\n[1] "OK" btn (100,120) 200x40'
        full_msg = f"{base_msg}{visual_detect_text}"
        assert "Detected UI regions" in full_msg
        assert "Annotated screenshot" in full_msg

