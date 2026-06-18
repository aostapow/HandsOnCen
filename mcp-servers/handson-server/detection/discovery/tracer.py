"""Discovery trace persistence."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Optional

_TRACE_DIR = Path.home() / ".handson" / "traces"


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def append_step(trace_id: str, step: dict[str, Any]) -> Path:
    _TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = _TRACE_DIR / f"discovery_{trace_id}.json"
    data: dict[str, Any]
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {"trace_id": trace_id, "steps": []}
    else:
        data = {"trace_id": trace_id, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
    step["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data["steps"].append(step)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def load_trace(trace_id: str) -> Optional[dict]:
    path = _TRACE_DIR / f"discovery_{trace_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
