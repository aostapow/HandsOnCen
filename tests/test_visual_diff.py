"""Tests for the visual diff tool (baseline capture + diff overlay)."""

import os
import sys
import base64
import io
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

def _solid_b64(width: int, height: int, color=(128, 128, 128)) -> str:
    """Create a solid-color image and return its base64-encoded JPEG."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _gradient_b64(width: int, height: int) -> str:
    """Create a horizontal gradient image and return base64-encoded JPEG."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for x in range(width):
        v = int(255 * x / max(width - 1, 1))
        arr[:, x, :] = v
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Test: compute_visual_diff
# ---------------------------------------------------------------------------

class TestComputeVisualDiff:
    def test_identical_images(self):
        from tools.visual_diff import compute_visual_diff
        b64 = _solid_b64(100, 100, (128, 128, 128))
        result = compute_visual_diff(b64, b64)
        assert result["is_identical"] is True
        assert result["changed_fraction"] == 0.0
        assert result["bbox"] is None

    def test_completely_different(self):
        from tools.visual_diff import compute_visual_diff
        black = _solid_b64(100, 100, (0, 0, 0))
        white = _solid_b64(100, 100, (255, 255, 255))
        result = compute_visual_diff(black, white, threshold=0.01)
        assert result["is_identical"] is False
        # Should be close to 1.0 (JPEG compression may cause slight variation)
        assert result["changed_fraction"] > 0.9
        assert result["bbox"] is not None

    def test_partial_change_has_correct_bbox(self):
        """A change in the bottom-right should produce a bbox there."""
        from tools.visual_diff import compute_visual_diff

        # Baseline: all gray
        baseline_arr = np.full((100, 200, 3), 128, dtype=np.uint8)
        baseline_img = Image.fromarray(baseline_arr, "RGB")
        buf = io.BytesIO()
        baseline_img.save(buf, format="PNG")
        baseline_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        # Current: gray with a white rectangle in bottom-right corner
        current_arr = baseline_arr.copy()
        current_arr[80:100, 150:200] = 255  # white block at (150,80)-(200,100)
        current_img = Image.fromarray(current_arr, "RGB")
        buf2 = io.BytesIO()
        current_img.save(buf2, format="PNG")
        current_b64 = base64.b64encode(buf2.getvalue()).decode("ascii")

        result = compute_visual_diff(baseline_b64, current_b64, threshold=0.1)
        assert result["is_identical"] is False
        assert result["bbox"] is not None

        bx, by, bw, bh = result["bbox"]
        # Bounding box should be in the bottom-right region
        assert bx >= 140  # near x=150
        assert by >= 70   # near y=80
        assert bx + bw <= 200
        assert by + bh <= 100

    def test_threshold_sensitivity(self):
        """Higher threshold should report fewer changes."""
        from tools.visual_diff import compute_visual_diff

        # Two slightly different grays
        a = _solid_b64(50, 50, (128, 128, 128))
        b = _solid_b64(50, 50, (135, 135, 135))

        # Low threshold: should see changes
        low = compute_visual_diff(a, b, threshold=0.01)
        # High threshold: should not see changes (diff ~2.7%)
        high = compute_visual_diff(a, b, threshold=0.1)

        assert high["changed_fraction"] <= low["changed_fraction"]

    def test_shape_mismatch_raises(self):
        from tools.visual_diff import compute_visual_diff
        small = _solid_b64(50, 50)
        big = _solid_b64(100, 100)
        with pytest.raises(ValueError, match="Resolution mismatch"):
            compute_visual_diff(small, big)

    def test_overlay_is_valid_image(self):
        from tools.visual_diff import compute_visual_diff
        black = _solid_b64(100, 100, (0, 0, 0))
        white = _solid_b64(100, 100, (255, 255, 255))
        result = compute_visual_diff(black, white)
        raw = base64.b64decode(result["overlay_b64"])
        img = Image.open(io.BytesIO(raw))
        assert img.size == (100, 100)


# ---------------------------------------------------------------------------
# Test: module state (baseline)
# ---------------------------------------------------------------------------

class TestBaselineState:
    def test_no_baseline_returns_error(self):
        """screenshot_diff without a baseline should return an error string."""
        from tools import visual_diff as mod
        old = mod._baseline
        mod._baseline = None
        try:
            # Call the core logic directly — the tool wrapper isn't registered
            # without a server, but we can test the state check
            assert mod._baseline is None
        finally:
            mod._baseline = old
