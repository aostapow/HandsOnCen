"""FlaUI C# sidecar backend — JSON-RPC over stdin/stdout."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Optional

from detection.backends.base import DetectionBackend
from detection.element_model import DetectedElement

_SIDECAR_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "handson-uia-sidecar",
    "publish",
    "handson-uia-sidecar.exe",
)


def _sidecar_available() -> bool:
    return sys.platform == "win32" and os.path.isfile(_SIDECAR_PATH)


def _call_sidecar(command: str, params: dict, timeout: float = 15.0) -> dict:
    if not _sidecar_available():
        return {"error": "FlaUI sidecar not built. Run build in handson-uia-sidecar/"}
    req = json.dumps({"Command": command, "Params": params})
    try:
        proc = subprocess.run(
            [_SIDECAR_PATH],
            input=req + "\n",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return {"error": proc.stderr or "sidecar failed"}
        return json.loads(proc.stdout.strip())
    except subprocess.TimeoutExpired:
        return {"error": "sidecar timeout"}
    except Exception as e:
        return {"error": str(e)}


def _dict_to_element(d: dict) -> DetectedElement:
    return DetectedElement(
        name=d.get("name", ""),
        role=d.get("role", ""),
        x=d.get("x", 0),
        y=d.get("y", 0),
        width=d.get("width", 0),
        height=d.get("height", 0),
        value=d.get("value", ""),
        backend="flaui",
        automation_id=d.get("automation_id", ""),
        class_name=d.get("class_name", ""),
        framework_id=d.get("framework_id", ""),
        enabled=d.get("enabled", True),
        visible=d.get("visible", True),
        patterns=d.get("patterns", []),
        raw_properties=d.get("raw_properties", {}),
    )


class FlaUIBackend(DetectionBackend):
    name = "flaui"

    def is_available(self) -> bool:
        return _sidecar_available()

    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 5,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> list[DetectedElement]:
        resp = _call_sidecar("list_tree", {
            "window_title": window_title or "",
            "max_depth": max_depth,
            "role": role or "",
            "tree_mode": tree_mode,
            "include_offscreen": include_offscreen,
        })
        if "error" in resp:
            return []
        return [_dict_to_element(e) for e in resp.get("elements", [])]

    def find_elements(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        automation_id: Optional[str] = None,
        class_name: Optional[str] = None,
        window_title: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
        index: int = 0,
    ) -> list[DetectedElement]:
        resp = _call_sidecar("find", {
            "name": name or "",
            "role": role or "",
            "automation_id": automation_id or "",
            "class_name": class_name or "",
            "window_title": window_title or "",
            "tree_mode": tree_mode,
            "include_offscreen": include_offscreen,
            "index": index,
        })
        if "error" in resp:
            return []
        return [_dict_to_element(e) for e in resp.get("elements", [])]

    def element_at_point(self, x: int, y: int) -> Optional[DetectedElement]:
        resp = _call_sidecar("from_point", {"x": x, "y": y})
        if "error" in resp or not resp.get("element"):
            return None
        return _dict_to_element(resp["element"])
