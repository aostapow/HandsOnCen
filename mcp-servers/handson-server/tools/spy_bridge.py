"""Bridge to handson-spy-sidecar for Spy-grade inspection."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


def _sidecar_exe() -> Optional[Path]:
    p = Path(__file__).resolve().parents[2] / "handson-spy-sidecar" / "publish" / "handson-spy-sidecar.exe"
    return p if p.exists() else None


def _call(command: str, params: dict) -> dict:
    exe = _sidecar_exe()
    if not exe:
        return {"found": False, "error": "handson-spy-sidecar not built"}
    req = json.dumps({"command": command, "params": params})
    try:
        proc = subprocess.run(
            [str(exe)],
            input=req,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout.strip())
        return {"found": False, "error": proc.stderr or "no output"}
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def spy_inspect_at(x: int, y: int) -> dict:
    return _call("from_point", {"x": x, "y": y})


def spy_inspect_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> dict:
    return _call("inspect_full", {
        "name": name or "",
        "automation_id": automation_id or "",
        "window_title": window_title or "",
    })


def spy_tree(
    window_title: str = "",
    mode: str = "control",
    max_depth: int = 5,
    visible_only: bool = False,
    role_filter: str = "",
) -> dict:
    return _call("walk_tree", {
        "window_title": window_title,
        "mode": mode,
        "max_depth": max_depth,
        "visible_only": visible_only,
        "role": role_filter,
    })


def spy_available() -> bool:
    return _sidecar_exe() is not None
