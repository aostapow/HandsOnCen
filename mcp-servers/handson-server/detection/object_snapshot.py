"""Post-interaction object snapshot — full props + image assets."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, Optional

from detection.object_repository import assets_path, load_repo, relative_asset, save_repo, upsert_object


def _phash(img) -> str:
    try:
        import numpy as np
        small = img.resize((8, 8)).convert("L")
        arr = np.array(small, dtype=float)
        avg = arr.mean()
        bits = (arr > avg).flatten()
        return hashlib.md5(bits.tobytes()).hexdigest()[:16]
    except Exception:
        return ""


def capture_object_snapshot(
    elem: dict,
    *,
    window_title: Optional[str] = None,
    repo_path: Optional[str] = None,
    app_name: str = "foreground",
    exe_path: str = "",
    full_properties: Optional[dict] = None,
    highlight: bool = False,
) -> dict:
    """Capture max detail + image assets for an interacted element."""
    from PIL import Image, ImageDraw
    from tools.screenshot import capture_screenshot
    from tools.image_utils import load_image_from_screenshot

    repo = load_repo(app_name, exe_path)
    app_id = repo["app_id"]
    x = elem.get("x", 0)
    y = elem.get("y", 0)
    w = elem.get("width", elem.get("w", 0))
    h = elem.get("height", elem.get("h", 0))
    if w <= 0 or h <= 0:
        return {"error": "no bbox"}

    shot = capture_screenshot(window_title=window_title)
    screen = load_image_from_screenshot(shot)

    pad = max(4, int(min(w, h) * 0.2))
    cx1 = max(0, x - pad)
    cy1 = max(0, y - pad)
    cx2 = min(screen.width, x + w + pad)
    cy2 = min(screen.height, y + h + pad)

    crop = screen.crop((x, y, x + w, y + h))
    context = screen.crop((cx1, cy1, cx2, cy2))
    template = crop.copy()

    annotated = screen.copy()
    draw = ImageDraw.Draw(annotated)
    for i in range(3):
        draw.rectangle([x - i, y - i, x + w + i, y + h + i], outline=(255, 0, 0))

    base = (repo_path or elem.get("name") or "object").replace("/", "_")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in base)[:64]
    ts = int(time.time())
    names = {
        "crop": f"{safe}_{ts}_crop.png",
        "context": f"{safe}_{ts}_context.png",
        "template": f"{safe}_{ts}_template.png",
        "annotated": f"{safe}_{ts}_annotated.png",
    }
    paths = {}
    for key, fname in names.items():
        p = assets_path(app_id, fname)
        {"crop": crop, "context": context, "template": template, "annotated": annotated}[key].save(p)
        paths[key] = relative_asset(app_id, fname)

    if not full_properties:
        full_properties = dict(elem)
        try:
            from tools.spy_bridge import spy_inspect_at
            spy = spy_inspect_at(x + w // 2, y + h // 2)
            if spy.get("found"):
                full_properties = spy.get("properties", full_properties)
        except Exception:
            pass

    snapshot = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "full_properties": full_properties,
        "images": paths,
        "phash": _phash(template),
        "bbox": {"x": x, "y": y, "w": w, "h": h},
    }

    if repo_path:
        upsert_object(
            repo,
            repo_path,
            snapshots={"latest": snapshot},
            last_resolution={
                "layer": elem.get("backend", "uia"),
                "backend": elem.get("backend", "uia"),
                "bbox": snapshot["bbox"],
            },
        )
    else:
        save_repo(repo)

    if highlight:
        try:
            from tools.highlight import highlight_rect
            highlight_rect(x, y, w, h)
        except Exception:
            pass

    return {"snapshot": snapshot, "app_id": app_id}
