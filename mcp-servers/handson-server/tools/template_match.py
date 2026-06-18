"""OpenCV template matching on window screenshots."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def find_by_template(
    image_path: str,
    window_title: Optional[str] = None,
    threshold: float = 0.75,
) -> dict:
    """Find UI element by template image path on current screen/window."""
    try:
        import cv2
        import numpy as np
        from tools.screenshot import capture_screenshot
        from tools.image_utils import load_image_from_screenshot
        from tools.windows import find_matching_window, do_list_windows

        template_path = Path(image_path)
        if not template_path.exists():
            return {"found": False, "error": f"template not found: {image_path}"}

        region = None
        if window_title:
            match = find_matching_window(window_title, do_list_windows())
            if match.get("window"):
                w = match["window"]
                region = {"x": w["x"], "y": w["y"], "w": w["width"], "h": w["height"]}

        shot = capture_screenshot(region=region)
        screen = load_image_from_screenshot(shot)
        offset_x = region["x"] if region else 0
        offset_y = region["y"] if region else 0

        screen_gray = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2GRAY)
        tmpl = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if tmpl is None:
            return {"found": False, "error": "could not read template image"}

        res = cv2.matchTemplate(screen_gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val < threshold:
            return {"found": False, "error": f"best match {max_val:.2f} below threshold {threshold}"}

        h, w = tmpl.shape[:2]
        x, y = max_loc
        return {
            "found": True,
            "confidence": float(max_val),
            "element": {
                "name": template_path.stem,
                "role": "template",
                "x": x + offset_x,
                "y": y + offset_y,
                "width": w,
                "height": h,
                "value": "",
                "backend": "template",
            },
        }
    except Exception as exc:
        return {"found": False, "error": str(exc)}
