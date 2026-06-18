"""Shared image loading helpers for screenshot/OCR/visual pipelines."""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Union

from PIL import Image

ImageSource = Union[Image.Image, str, bytes, dict]


def load_image(source: ImageSource) -> Image.Image:
    """Load a PIL Image from path, bytes, base64 dict, or pass-through Image."""
    if isinstance(source, Image.Image):
        return source
    if isinstance(source, dict):
        if "image" in source:
            return load_image(source["image"])
        if "path" in source:
            return Image.open(source["path"]).convert("RGB")
        raise ValueError("dict source must have 'image' or 'path'")
    if isinstance(source, bytes):
        return Image.open(io.BytesIO(source)).convert("RGB")
    if isinstance(source, str):
        if source.startswith("data:image"):
            b64 = source.split(",", 1)[-1]
            return load_image(base64.b64decode(b64))
        try:
            raw = base64.b64decode(source, validate=True)
            return load_image(raw)
        except Exception:
            return Image.open(Path(source)).convert("RGB")
    raise TypeError(f"unsupported image source: {type(source)}")


def load_image_from_screenshot(shot: dict) -> Image.Image:
    """Decode capture_screenshot() result to PIL Image."""
    return load_image(base64.b64decode(shot["image"]))


def region_to_element_dict(region: dict, backend: str = "visual") -> dict:
    """Map visual_detect region (w/h) to legacy element dict (width/height)."""
    w = region.get("width", region.get("w", 0))
    h = region.get("height", region.get("h", 0))
    return {
        "name": region.get("text", region.get("name", "")),
        "role": region.get("type", region.get("class", "panel")),
        "x": region.get("x", 0),
        "y": region.get("y", 0),
        "width": w,
        "height": h,
        "value": "",
        "backend": backend,
    }
