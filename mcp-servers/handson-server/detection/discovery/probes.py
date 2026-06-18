"""Probe catalog for methodical UI discovery."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

SAFE_MODE_BLACKLIST = re.compile(
    r"\b(DELETE|REMOVE|FORMAT|EXIT|QUIT|SUBMIT|SAVE|DISCARD|UNINSTALL|SHUTDOWN)\b",
    re.IGNORECASE,
)

PROBE_IDS = (
    "verify_context",
    "rescan",
    "list_modals",
    "expand_menu",
    "switch_tab",
    "expand_tree",
    "scroll_panel",
    "access_key",
    "dismiss_overlay",
    "find_by_template",
)


@dataclass
class ProbeSpec:
    id: str
    target: str = ""
    reason: str = ""
    risk: str = "low"
    revert: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def is_safe_target(name: str, safe_mode: bool = True) -> bool:
    if not safe_mode or not name:
        return True
    return SAFE_MODE_BLACKLIST.search(name) is None


def default_probe_order(framework: str) -> list[str]:
    base = ["verify_context", "rescan", "list_modals"]
    if framework in ("winforms", "win32", "mfc"):
        return base + ["expand_menu", "access_key", "switch_tab", "expand_tree", "scroll_panel"]
    if framework in ("electron", "chromium_browser"):
        return base + ["switch_tab", "scroll_panel", "expand_menu"]
    if framework == "java_swing":
        return base + ["scroll_panel", "expand_tree"]
    return base + ["expand_menu", "switch_tab", "expand_tree", "scroll_panel", "access_key"]
