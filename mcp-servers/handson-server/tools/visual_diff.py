"""Visual diff tools -- before/after screenshot comparison.

Provides:
    screenshot_baseline  - capture a reference screenshot
    screenshot_diff      - capture current screen and highlight changes vs baseline

The diff overlay paints changed pixels in semi-transparent red and draws
a bounding box around the changed region.  Useful for verifying that a
code change produced the expected visual result.
"""

import base64
import io
import time
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

from tools.screenshot import (
    capture_screenshot,
    _b64_to_array,
    _build_region,
)

# ------------------------------------------------------------------
# Module state
# ------------------------------------------------------------------

_baseline: Optional[dict] = None  # {b64, width, height, monitor, region, timestamp}


# ------------------------------------------------------------------
# Core algorithm
# ------------------------------------------------------------------

def compute_visual_diff(
    baseline_b64: str,
    current_b64: str,
    threshold: float = 0.02,
    highlight_color: tuple[int, int, int, int] = (255, 0, 0, 100),
) -> dict:
    """Compare two base64-encoded images and produce a diff overlay.

    Parameters
    ----------
    baseline_b64 : str
        Base64-encoded baseline image.
    current_b64 : str
        Base64-encoded current image.
    threshold : float
        Per-pixel diff threshold in [0, 1].  Pixels whose max-channel
        normalised difference exceeds this are marked as changed.
    highlight_color : tuple
        RGBA color for the changed-pixel overlay.

    Returns
    -------
    dict
        ``{"overlay_b64": str, "changed_fraction": float,
          "is_identical": bool, "bbox": tuple|None,
          "current_b64": str}``
        *bbox* is ``(x, y, w, h)`` of the tightest rectangle around all
        changed pixels, or ``None`` when identical.
    """
    baseline_arr = _b64_to_array(baseline_b64)
    current_arr = _b64_to_array(current_b64)

    # Shape mismatch → treat as fully different
    if baseline_arr.shape != current_arr.shape:
        raise ValueError(
            f"Resolution mismatch: baseline {baseline_arr.shape[:2][::-1]} "
            f"vs current {current_arr.shape[:2][::-1]}"
        )

    # Per-pixel diff: max across RGB channels, normalised to [0, 1]
    diff = np.abs(baseline_arr.astype(float) - current_arr.astype(float)) / 255.0
    if diff.ndim == 3:
        channel_max = np.max(diff, axis=2)
    else:
        channel_max = diff

    mask = channel_max > threshold
    changed_fraction = float(np.mean(mask))
    is_identical = changed_fraction == 0.0

    # Build overlay image: current screenshot + semi-transparent highlight
    current_img = Image.open(io.BytesIO(base64.b64decode(current_b64))).convert("RGBA")
    overlay = Image.new("RGBA", current_img.size, (0, 0, 0, 0))
    overlay_arr = np.array(overlay)

    # Paint changed pixels
    overlay_arr[mask] = highlight_color

    bbox = None
    if not is_identical:
        # Compute bounding box of changed region
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        y_min, y_max = int(np.argmax(rows)), int(mask.shape[0] - 1 - np.argmax(rows[::-1]))
        x_min, x_max = int(np.argmax(cols)), int(mask.shape[1] - 1 - np.argmax(cols[::-1]))
        bbox = (x_min, y_min, x_max - x_min + 1, y_max - y_min + 1)

        # Draw bounding box rectangle on overlay
        overlay_pil = Image.fromarray(overlay_arr, "RGBA")
        draw = ImageDraw.Draw(overlay_pil)
        draw.rectangle(
            [(x_min, y_min), (x_max, y_max)],
            outline=(255, 0, 0, 200),
            width=2,
        )
        overlay_arr = np.array(overlay_pil)

    # Composite overlay onto current image
    overlay_pil = Image.fromarray(overlay_arr, "RGBA")
    composited = Image.alpha_composite(current_img, overlay_pil)

    # Encode result as JPEG
    composited_rgb = composited.convert("RGB")
    buf = io.BytesIO()
    composited_rgb.save(buf, format="JPEG", quality=85)
    overlay_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "overlay_b64": overlay_b64,
        "changed_fraction": changed_fraction,
        "is_identical": is_identical,
        "bbox": bbox,
        "current_b64": current_b64,
    }


# ------------------------------------------------------------------
# MCP tool registration
# ------------------------------------------------------------------

def register(server) -> int:
    """Register *screenshot_baseline* and *screenshot_diff* tools.

    Returns the number of tools registered (2).
    """
    from mcp.server.fastmcp import Image as McpImage
    from tools.safety import with_timeout, ActionTimeoutError

    @server.tool()
    def screenshot_baseline(
        monitor: int = 0,
        region_x: int | None = None,
        region_y: int | None = None,
        region_w: int | None = None,
        region_h: int | None = None,
    ) -> list:
        """Capture a baseline screenshot for later visual comparison.

        Call this before making a change, then use screenshot_diff after
        the change to see exactly what moved.  Uses the same monitor/region
        params as screenshot.
        """
        global _baseline
        region = _build_region(region_x, region_y, region_w, region_h)

        try:
            result = with_timeout(
                lambda: capture_screenshot(
                    monitor_index=monitor if monitor != 0 else None,
                    region=region,
                ),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return "Timed out after 5s capturing baseline. Display may be unresponsive."

        _baseline = {
            "b64": result["image"],
            "width": result["width"],
            "height": result["height"],
            "monitor": monitor,
            "region": region,
            "timestamp": time.time(),
        }

        return [
            McpImage(data=base64.b64decode(result["image"]), format="png"),
            f"Baseline captured: {result['width']}x{result['height']}. "
            f"Now make your change, then call screenshot_diff to compare.",
        ]

    @server.tool()
    def screenshot_diff(
        threshold: float = 0.02,
    ) -> list:
        """Compare the current screen against the stored baseline.

        Returns an overlay image highlighting changed pixels in red, with
        a bounding box around the changed region.  Call screenshot_baseline
        first to set the reference.

        Parameters:
            threshold: Pixel diff sensitivity (0.0-1.0). Lower = more sensitive.
                       Default 0.02 catches subtle changes without noise.
        """
        global _baseline

        if _baseline is None:
            return "No baseline set. Call screenshot_baseline first."

        # Recapture with same monitor/region as baseline
        region = _baseline["region"]
        monitor = _baseline["monitor"]

        try:
            result = with_timeout(
                lambda: capture_screenshot(
                    monitor_index=monitor if monitor != 0 else None,
                    region=region,
                ),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return "Timed out after 5s capturing current screenshot."

        # Compute diff
        try:
            diff = compute_visual_diff(
                _baseline["b64"],
                result["image"],
                threshold=threshold,
            )
        except ValueError as e:
            return f"Diff failed: {e}"

        if diff["is_identical"]:
            return [
                McpImage(data=base64.b64decode(result["image"]), format="png"),
                "No changes detected. Screen is identical to baseline.",
            ]

        pct = diff["changed_fraction"] * 100
        bbox = diff["bbox"]
        summary = f"Changed: {pct:.1f}%"
        if bbox:
            summary += f" — bounding box at ({bbox[0]},{bbox[1]}) {bbox[2]}x{bbox[3]}"

        return [
            McpImage(data=base64.b64decode(diff["overlay_b64"]), format="png"),
            summary,
        ]

    return 2

