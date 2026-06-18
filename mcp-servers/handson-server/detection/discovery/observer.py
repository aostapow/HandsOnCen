"""Structured UI observation snapshot."""
from __future__ import annotations

from typing import Any, Optional


def observe_ui(
    window_title: Optional[str] = None,
    hints: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Capture methodical observation of current UI state."""
    import sys

    obs: dict[str, Any] = {
        "window_title": window_title or "",
        "framework": "unknown",
        "exe_name": "",
        "exe_path": "",
        "fingerprint": "",
        "element_count": 0,
        "named_count": 0,
        "tree_sample": [],
        "menu_bars": [],
        "tabs": [],
        "trees": [],
        "modals": [],
        "screenshot_path": "",
        "ocr_sample": [],
    }

    try:
        from tools.framework_detect import do_detect_framework
        fw = do_detect_framework(window_title)
        obs["framework"] = fw.get("framework", "unknown")
        obs["exe_name"] = fw.get("process_name") or fw.get("exe_name") or ""
        obs["exe_path"] = fw.get("exe_path", "")
        obs["framework_hints"] = fw.get("hints", [])
    except Exception:
        pass

    try:
        from tools.ui_automation import do_ui_fingerprint
        fp = do_ui_fingerprint(window_title=window_title)
        obs["fingerprint"] = fp.get("hash", "")
        obs["element_count"] = fp.get("element_count", 0)
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            from tools.ui_automation import do_list_elements
            result = do_list_elements(window_title=window_title, max_depth=5)
            elements = result.get("elements", [])
            obs["element_count"] = result.get("count", len(elements))
            named = [e for e in elements if e.get("name")]
            obs["named_count"] = len(named)
            obs["tree_sample"] = elements[:40]
            for e in elements:
                role = (e.get("role") or "").lower()
                name = e.get("name") or ""
                if "menu" in role and "bar" in role:
                    obs["menu_bars"].append({"name": name, **e})
                elif "tab" in role:
                    obs["tabs"].append({"name": name, **e})
                elif "tree" in role:
                    obs["trees"].append({"name": name, **e})
        except Exception:
            pass

    try:
        from tools.windows import do_list_windows
        windows = do_list_windows()
        if windows:
            main = windows[0]
            obs["foreground_window"] = main.get("title", "")
            for w in windows[1:6]:
                if w.get("title") and w.get("title") != main.get("title"):
                    obs["modals"].append({"title": w.get("title"), "x": w.get("x"), "y": w.get("y")})
    except Exception:
        pass

    try:
        from tools.screenshot import capture_screenshot
        from tools.windows import find_matching_window, do_list_windows
        region = None
        if window_title:
            match = find_matching_window(window_title, do_list_windows())
            if match.get("window"):
                w = match["window"]
                region = {"x": w["x"], "y": w["y"], "w": w["width"], "h": w["height"]}
        shot = capture_screenshot(region=region)
        obs["screenshot_path"] = shot.get("path", "")
    except Exception:
        pass

    if hints:
        try:
            from tools.ocr import do_find_text_dual
            for hint in hints[:3]:
                ocr = do_find_text_dual(hint, window_title=window_title)
                for m in ocr.get("matches", [])[:5]:
                    obs["ocr_sample"].append(m)
        except Exception:
            pass

    return obs
