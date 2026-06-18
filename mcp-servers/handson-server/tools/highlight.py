"""On-screen element highlight overlay (Automation Spy style red border)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

_OVERLAY_PROC = None


def _sidecar_path() -> Optional[Path]:
    p = Path(__file__).resolve().parents[2] / "handson-spy-sidecar" / "publish" / "handson-spy-sidecar.exe"
    if p.exists():
        return p
    return None


def _call_sidecar(command: str, params: dict) -> dict:
    exe = _sidecar_path()
    if not exe:
        return {"error": "spy sidecar not built"}
    req = json.dumps({"Command": command, "Params": params})
    try:
        proc = subprocess.run(
            [str(exe)],
            input=req,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout.strip())
        return {"error": proc.stderr or "no output"}
    except Exception as exc:
        return {"error": str(exc)}


def highlight_rect(
    x: int, y: int, w: int, h: int,
    *,
    duration_ms: int = 3000,
    color: str = "red",
) -> dict:
    """Draw red border overlay around rectangle."""
    global _OVERLAY_PROC
    result = _call_sidecar("highlight", {
        "x": x, "y": y, "w": w, "h": h,
        "duration_ms": duration_ms,
        "color": color,
    })
    if "error" in result and sys.platform == "win32":
        return _highlight_win32_fallback(x, y, w, h, duration_ms)
    return result


def clear_highlight() -> dict:
    return _call_sidecar("unhighlight", {})


def highlight_element_dict(elem: dict, duration_ms: int = 3000) -> dict:
    x = elem.get("x", 0)
    y = elem.get("y", 0)
    w = elem.get("width", elem.get("w", 0))
    h = elem.get("height", elem.get("h", 0))
    if w <= 0 or h <= 0:
        return {"error": "element has no bounding box"}
    return highlight_rect(x, y, w, h, duration_ms=duration_ms)


def _highlight_win32_fallback(x: int, y: int, w: int, h: int, duration_ms: int) -> dict:
    """Python-only fallback: flash via screenshot annotation path (no overlay)."""
    try:
        from PIL import Image, ImageDraw
        from tools.screenshot import capture_screenshot
        from tools.image_utils import load_image_from_screenshot

        shot = capture_screenshot()
        img = load_image_from_screenshot(shot)
        draw = ImageDraw.Draw(img)
        thickness = 3
        for i in range(thickness):
            draw.rectangle(
                [x - i, y - i, x + w + i, y + h + i],
                outline=(255, 0, 0),
            )
        out = Path(shot["path"]).with_name("highlight_annotated.png")
        img.save(out)
        return {"annotated_path": str(out), "fallback": True, "duration_ms": duration_ms}
    except Exception as exc:
        return {"error": str(exc)}
