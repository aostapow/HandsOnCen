"""Persistent strategy memory — which layer/backend worked per object."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

_MEMORY_PATH = Path.home() / ".handson" / "strategy_memory.json"
_TTL_DAYS = 30


def _load() -> dict:
  if not _MEMORY_PATH.exists():
    return {}
  try:
    return json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
  except Exception:
    return {}


def _save(data: dict) -> None:
  _MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
  _MEMORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def make_key(app_name: str, window: str, object_id: str) -> str:
  return f"{app_name}|{window}|{object_id}"


def get_strategy(key: str) -> Optional[dict]:
  entry = _load().get(key)
  if not entry:
    return None
  ts = entry.get("updated_at", 0)
  if time.time() - ts > _TTL_DAYS * 86400:
    return None
  return entry


def record_success(
  key: str,
  *,
  layer: str,
  backend: str,
  fallback_order: list[str] | None = None,
) -> None:
  data = _load()
  entry = data.get(key, {"hits": 0, "misses": 0})
  entry["preferred_layer"] = layer
  entry["preferred_backend"] = backend
  if fallback_order:
    entry["fallback_order"] = fallback_order
  entry["hits"] = entry.get("hits", 0) + 1
  entry["updated_at"] = time.time()
  data[key] = entry
  _save(data)


def record_miss(key: str) -> None:
  data = _load()
  entry = data.get(key, {"hits": 0, "misses": 0})
  entry["misses"] = entry.get("misses", 0) + 1
  entry["updated_at"] = time.time()
  data[key] = entry
  _save(data)
