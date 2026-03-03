"""Vision tools -- screen capture and wait-for-change detection.

Provides:
    capture_screenshot  - grab the screen (or a region) via mss
    crop_region         - crop a PIL Image to {x, y, w, h}
    wait_for_change     - poll until the screen changes or timeout
    register            - wire the above as MCP tools on a Server
"""

import base64
import io
import time
from typing import Optional

import mss
import numpy as np
from PIL import Image

from screenshot_manager import ScreenshotManager

# Lazy-initialised mss instance (reused across calls).
_sct: Optional[mss.mss] = None

# The screenshot manager is injected at import time from server.py.
# For tests, callers can mock this attribute directly.
screenshot_manager: Optional[ScreenshotManager] = None

# Max width for screenshots sent to Claude. Images wider than this are
# downscaled proportionally.  1280px is the sweet spot: all UI text,
# buttons, and labels remain readable while cutting payload ~17x vs
# raw 5K PNGs (119KB JPEG vs ~2MB PNG).
MAX_SCREENSHOT_WIDTH = 1280


# ------------------------------------------------------------------
# DPI scaling
# ------------------------------------------------------------------

# Cached DPI scale (queried once at first use)
_dpi_scale: Optional[float] = None


def _query_dpi() -> float:
    """Query the primary monitor's DPI scale factor via platform backend."""
    try:
        from handson_platform import get_dpi_scale as _plat_dpi
        return _plat_dpi()
    except (ImportError, NotImplementedError):
        return 1.0


def get_dpi_scale() -> float:
    """Get the cached DPI scale factor."""
    global _dpi_scale
    if _dpi_scale is None:
        _dpi_scale = _query_dpi()
    return _dpi_scale


def physical_to_logical(x: int, y: int, scale: Optional[float] = None) -> tuple[int, int]:
    """Convert physical (screenshot) pixels to logical (input) pixels."""
    if scale is None:
        scale = get_dpi_scale()
    if scale == 1.0:
        return (x, y)
    return (int(x / scale), int(y / scale))


def logical_to_physical(x: int, y: int, scale: Optional[float] = None) -> tuple[int, int]:
    """Convert logical (input) pixels to physical (screenshot) pixels."""
    if scale is None:
        scale = get_dpi_scale()
    if scale == 1.0:
        return (x, y)
    return (int(x * scale), int(y * scale))


# ------------------------------------------------------------------
# Helper: region assembly
# ------------------------------------------------------------------

def _build_region(
    x: Optional[int],
    y: Optional[int],
    w: Optional[int],
    h: Optional[int],
) -> Optional[dict]:
    """Build a region dict from individual x/y/w/h params.

    Returns None if any parameter is None.
    """
    if x is None or y is None or w is None or h is None:
        return None
    return {"x": x, "y": y, "w": w, "h": h}


# ------------------------------------------------------------------
# Core functions
# ------------------------------------------------------------------

def crop_region(img: Image.Image, region: dict) -> Image.Image:
    """Crop *img* to the rectangle described by *region*.

    Parameters
    ----------
    img : PIL.Image.Image
        Source image.
    region : dict
        ``{"x": int, "y": int, "w": int, "h": int}``

    Returns
    -------
    PIL.Image.Image
        The cropped image.
    """
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    return img.crop((x, y, x + w, y + h))


def capture_screenshot(
    monitor_index: Optional[int] = None,
    region: Optional[dict] = None,
) -> dict:
    """Capture the screen (or a region) and return metadata + base64 PNG.

    Parameters
    ----------
    monitor_index : int | None
        0 = all monitors combined, 1 = primary, 2 = second, etc.
        Defaults to 1 (primary) when None.
    region : dict | None
        ``{"x": int, "y": int, "w": int, "h": int}`` to crop after capture.

    Returns
    -------
    dict
        ``{"image": str, "width": int, "height": int, "path": str}``
    """
    global _sct

    if _sct is None:
        _sct = mss.mss()

    if monitor_index is None:
        monitor_index = 1

    try:
        monitor = _sct.monitors[monitor_index]
        shot = _sct.grab(monitor)
    except Exception:
        # Stale DC handle (e.g. after MCP reconnect) — recreate
        _sct = mss.mss()
        monitor = _sct.monitors[monitor_index]
        shot = _sct.grab(monitor)

    # Convert mss screenshot to PIL Image
    img = Image.frombytes("RGB", shot.size, shot.rgb)

    # Optionally crop
    if region is not None:
        img = crop_region(img, region)

    # Downscale if wider than MAX_SCREENSHOT_WIDTH
    if img.width > MAX_SCREENSHOT_WIDTH:
        scale = MAX_SCREENSHOT_WIDTH / img.width
        new_h = int(img.height * scale)
        img = img.resize((MAX_SCREENSHOT_WIDTH, new_h), Image.LANCZOS)

    # Encode as JPEG (much smaller than PNG for screenshots)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    png_bytes = buf.getvalue()  # name kept for compat

    # Save to disk via the screenshot manager
    path = screenshot_manager.save(png_bytes)

    # Base64 encode for MCP transport
    b64 = base64.b64encode(png_bytes).decode("ascii")

    return {
        "image": b64,
        "width": img.width,
        "height": img.height,
        "path": path,
        "dpi_scale": get_dpi_scale(),
    }


def wait_for_change(
    timeout: float = 5.0,
    threshold: float = 0.01,
    poll_interval: float = 0.5,
    region: Optional[dict] = None,
    monitor_index: Optional[int] = None,
) -> dict:
    """Poll the screen until it changes or *timeout* elapses.

    Captures a baseline screenshot, then repeatedly captures and compares.
    The comparison uses mean absolute pixel difference normalised to [0, 1].

    Parameters
    ----------
    timeout : float
        Maximum seconds to wait.
    threshold : float
        Minimum normalised diff to count as "changed".
    poll_interval : float
        Seconds between captures.
    region, monitor_index :
        Forwarded to :func:`capture_screenshot`.

    Returns
    -------
    dict
        ``{"changed": bool, "elapsed": float, "image": str,
          "width": int, "height": int, "path": str}``
    """
    cap_kwargs = {}
    if region is not None:
        cap_kwargs["region"] = region
    if monitor_index is not None:
        cap_kwargs["monitor_index"] = monitor_index

    baseline = capture_screenshot(**cap_kwargs)

    start = time.monotonic()
    latest = baseline

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            return {
                "changed": False,
                "elapsed": elapsed,
                "image": latest["image"],
                "width": latest["width"],
                "height": latest["height"],
                "path": latest["path"],
            }

        time.sleep(poll_interval)

        current = capture_screenshot(**cap_kwargs)
        diff = compare_screenshots(baseline["image"], current["image"])

        latest = current

        if diff >= threshold:
            return {
                "changed": True,
                "elapsed": time.monotonic() - start,
                "image": current["image"],
                "width": current["width"],
                "height": current["height"],
                "path": current["path"],
            }


def get_screen_size() -> list:
    """Return dimensions of all available monitors.

    Index 0 is the combined virtual screen; 1+ are individual monitors.
    """
    global _sct
    if _sct is None:
        _sct = mss.mss()

    try:
        _ = _sct.monitors  # probe for stale handle
    except Exception:
        _sct = mss.mss()

    monitors = []
    for i, mon in enumerate(_sct.monitors):
        monitors.append({
            "index": i,
            "x": mon["left"],
            "y": mon["top"],
            "width": mon["width"],
            "height": mon["height"],
            "dpi_scale": get_dpi_scale(),
        })
    return monitors


# ------------------------------------------------------------------
# Annotation
# ------------------------------------------------------------------

def annotate_image(
    img: Image.Image,
    grid: bool = True,
    mouse_pos: Optional[tuple[int, int]] = None,
    elements: Optional[list[dict]] = None,
    grid_spacing: int = 500,
) -> Image.Image:
    """Draw annotation overlays on a copy of img.

    Parameters:
        img: Source screenshot
        grid: Draw grid lines with coordinate labels
        mouse_pos: (x, y) tuple to draw crosshair at
        elements: List of element dicts with x, y, width, height, name, role
        grid_spacing: Pixels between grid lines (default 500)
    """
    from PIL import ImageDraw, ImageFont

    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except (IOError, OSError):
        font = ImageFont.load_default()

    w, h = img.size
    grid_color = (128, 128, 128, 128)  # Semi-transparent gray
    text_color = (200, 200, 200)

    if grid:
        # Vertical lines
        for x in range(0, w, grid_spacing):
            draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
            draw.text((x + 2, 2), str(x), fill=text_color, font=font)
        # Horizontal lines
        for y in range(0, h, grid_spacing):
            draw.line([(0, y), (w, y)], fill=grid_color, width=1)
            draw.text((2, y + 2), str(y), fill=text_color, font=font)

    if mouse_pos:
        mx, my = mouse_pos
        cross_size = 20
        cross_color = (255, 0, 0)  # Red
        draw.line([(mx - cross_size, my), (mx + cross_size, my)], fill=cross_color, width=2)
        draw.line([(mx, my - cross_size), (mx, my + cross_size)], fill=cross_color, width=2)
        draw.text((mx + 5, my + 5), f"({mx},{my})", fill=cross_color, font=font)

    if elements:
        elem_color = (0, 255, 128)  # Green
        for i, elem in enumerate(elements):
            x, y = elem["x"], elem["y"]
            r = x + elem["width"]
            b = y + elem["height"]
            draw.rectangle([(x, y), (r, b)], outline=elem_color, width=2)
            label = f"[{i}] {elem.get('role', '')} {elem.get('name', '')}"
            draw.text((x, y - 16), label, fill=elem_color, font=font)

    return annotated


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _b64_to_array(b64_str: str) -> np.ndarray:
    """Decode a base64 PNG string to a numpy uint8 array."""
    raw = base64.b64decode(b64_str)
    img = Image.open(io.BytesIO(raw))
    return np.array(img, dtype=np.uint8)


def compare_screenshots(before_b64: str, after_b64: str) -> float:
    """Normalised pixel diff [0.0, 1.0]. 0=identical, 1=max different."""
    before_arr = _b64_to_array(before_b64)
    after_arr = _b64_to_array(after_b64)
    if before_arr.shape != after_arr.shape:
        return 1.0
    return float(np.mean(np.abs(before_arr.astype(float) - after_arr.astype(float))) / 255.0)


# ------------------------------------------------------------------
# MCP tool registration
# ------------------------------------------------------------------

def register(server) -> int:
    """Register *screenshot* and *wait_for_change* tools on *server*.

    Returns the number of tools registered (2).
    """
    from mcp.server.fastmcp import Image as McpImage

    from tools.safety import with_timeout, ActionTimeoutError

    @server.tool()
    def screenshot(
        monitor: int = 0,
        region_x: int | None = None,
        region_y: int | None = None,
        region_w: int | None = None,
        region_h: int | None = None,
        annotate: bool = False,
    ) -> list:
        """Capture a screenshot of the screen or a region.

        Returns the image so you can see what's on screen.
        Use monitor=0 for all monitors, monitor=1 for primary, etc.
        Optionally crop to a region with region_x/y/w/h.
        Set annotate=True to overlay grid lines, mouse position, and UI element outlines.
        """
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
            return "Timed out after 5s capturing screenshot. Display may be unresponsive."

        if annotate:
            raw_img = Image.open(io.BytesIO(base64.b64decode(result["image"])))
            mouse_pos = None
            try:
                import pyautogui
                pos = pyautogui.position()
                mouse_pos = (pos[0], pos[1])
            except Exception:
                pass
            elements = None
            try:
                from tools.ui_automation import do_list_elements
                elem_result = do_list_elements(max_depth=2)
                elements = elem_result.get("elements", [])
            except Exception:
                pass
            focus_info = ""
            try:
                from tools.ui_automation import do_get_focused_element
                focus_result = do_get_focused_element()
                if focus_result["found"]:
                    fe = focus_result["element"]
                    focus_info = f" Focused: {fe['role']} \"{fe['name']}\" at ({fe['x']},{fe['y']})"
            except Exception:
                pass

            annotated = annotate_image(raw_img, grid=True, mouse_pos=mouse_pos, elements=elements)
            buf = io.BytesIO()
            annotated.save(buf, format="PNG")
            return [
                McpImage(data=buf.getvalue(), format="png"),
                f"Annotated screenshot: {result['width']}x{result['height']} pixels. File: {result['path']}{focus_info}",
            ]

        return [
            McpImage(data=base64.b64decode(result["image"]), format="png"),
            f"Screenshot captured: {result['width']}x{result['height']} pixels. File: {result['path']}",
        ]

    @server.tool()
    def wait_for_change(
        timeout: float = 5.0,
        threshold: float = 0.01,
        poll_interval: float = 0.5,
        monitor: int = 0,
        region_x: int | None = None,
        region_y: int | None = None,
        region_w: int | None = None,
        region_h: int | None = None,
    ) -> list:
        """Wait until the screen content changes or timeout elapses.

        Use after clicking a button or triggering an action to wait for the
        UI to respond. Returns when change is detected or timeout expires.
        threshold is the fraction of pixels that must differ (0.01 = 1%).
        """
        from tools.screenshot import wait_for_change as _wait

        region = _build_region(region_x, region_y, region_w, region_h)
        try:
            result = with_timeout(
                lambda: _wait(
                    timeout=timeout,
                    threshold=threshold,
                    poll_interval=poll_interval,
                    region=region,
                    monitor_index=monitor if monitor != 0 else None,
                ),
                timeout=timeout + 5.0,
            )
        except ActionTimeoutError:
            return f"Timed out after {timeout + 5.0:.0f}s waiting for screen change. Display may be unresponsive."

        status = "changed" if result["changed"] else "unchanged"
        return [
            McpImage(data=base64.b64decode(result["image"]), format="png"),
            f"Screen {status} after {result['elapsed']:.1f}s. {result['width']}x{result['height']} pixels. File: {result['path']}",
        ]

    @server.tool()
    def get_screen_size() -> str:
        """Get the dimensions of all connected monitors.

        Returns monitor index, position (x, y), and size (width x height)
        for each display. Index 0 is the combined virtual screen spanning
        all monitors; index 1+ are individual monitors.
        """
        from tools.screenshot import get_screen_size as _get_size
        try:
            monitors = with_timeout(_get_size, timeout=3.0)
        except ActionTimeoutError:
            return "Timed out after 3s querying monitors."
        if not monitors:
            return "No monitors detected."
        lines = [f"Detected {len(monitors)} monitor entries:"]
        for m in monitors:
            label = "Combined" if m["index"] == 0 else f"Monitor {m['index']}"
            lines.append(
                f"  {label}: {m['width']}x{m['height']} at ({m['x']}, {m['y']})"
            )
        return "\n".join(lines)

    return 3
