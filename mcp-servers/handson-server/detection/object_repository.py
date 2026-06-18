"""UFT-style object repository with image snapshots."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

_REPO_DIR = Path.home() / ".handson" / "repositories"


def _app_id(app_name: str, exe_path: str = "") -> str:
  raw = exe_path or app_name
  return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _repo_path(app_id: str) -> Path:
  return _REPO_DIR / f"{app_id}.json"


def _assets_dir(app_id: str) -> Path:
  d = _REPO_DIR / app_id / "assets"
  d.mkdir(parents=True, exist_ok=True)
  return d


def load_repo(app_name: str, exe_path: str = "") -> dict:
  aid = _app_id(app_name, exe_path)
  path = _repo_path(aid)
  if path.exists():
    try:
      return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
      pass
  return {
    "app_id": aid,
    "app_name": app_name,
    "framework": "unknown",
    "windows": {},
  }


def save_repo(repo: dict) -> None:
  _REPO_DIR.mkdir(parents=True, exist_ok=True)
  path = _repo_path(repo["app_id"])
  path.write_text(json.dumps(repo, indent=2), encoding="utf-8")


def _ensure_window(repo: dict, window_key: str, title_pattern: str = "") -> dict:
  windows = repo.setdefault("windows", {})
  if window_key not in windows:
    windows[window_key] = {
      "title_pattern": title_pattern or f".*{re.escape(window_key)}.*",
      "objects": {},
    }
  return windows[window_key]


def get_object(repo: dict, repo_path: str) -> Optional[dict]:
  """repo_path: 'windowKey/objectName'"""
  parts = repo_path.split("/", 1)
  if len(parts) != 2:
    return None
  win_key, obj_name = parts
  return repo.get("windows", {}).get(win_key, {}).get("objects", {}).get(obj_name)


def upsert_object(
  repo: dict,
  repo_path: str,
  *,
  obj_class: str = "control",
  identification: dict | None = None,
  last_resolution: dict | None = None,
  snapshots: dict | None = None,
  parent: str = "",
) -> dict:
  parts = repo_path.split("/", 1)
  if len(parts) != 2:
    raise ValueError("repo_path must be 'windowKey/objectName'")
  win_key, obj_name = parts
  window = _ensure_window(repo, win_key)
  objects = window.setdefault("objects", {})
  obj = objects.setdefault(obj_name, {"class": obj_class, "parent": parent})
  if identification:
    obj["identification"] = identification
  if last_resolution:
    lr = obj.setdefault("last_resolution", {})
    lr.update(last_resolution)
    lr["success_count"] = lr.get("success_count", 0) + 1
    lr["last_success"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  if snapshots:
    obj["snapshots"] = snapshots
  save_repo(repo)
  return obj


def list_objects(repo: dict, window_key: str | None = None) -> list[dict]:
  result = []
  windows = repo.get("windows", {})
  targets = {window_key: windows[window_key]} if window_key and window_key in windows else windows
  for wk, wdata in targets.items():
    for name, obj in wdata.get("objects", {}).items():
      result.append({"repo_path": f"{wk}/{name}", **obj})
  return result


def assets_path(app_id: str, filename: str) -> Path:
  return _assets_dir(app_id) / filename


def relative_asset(app_id: str, filename: str) -> str:
  return f"{app_id}/assets/{filename}"
