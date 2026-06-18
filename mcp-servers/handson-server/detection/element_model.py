"""Unified element model for all detection backends."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class DetectedElement:
    """Normalized UI element from any backend."""

    name: str = ""
    role: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    value: str = ""
    backend: str = "uia"
    automation_id: str = ""
    class_name: str = ""
    framework_id: str = ""
    runtime_id: str = ""
    process_id: int = 0
    hwnd: int = 0
    enabled: bool = True
    visible: bool = True
    has_focus: bool = False
    is_keyboard_focusable: bool = False
    access_key: str = ""
    help_text: str = ""
    localized_control_type: str = ""
    aria_role: str = ""
    aria_properties: str = ""
    clickable_x: Optional[int] = None
    clickable_y: Optional[int] = None
    patterns: list[str] = field(default_factory=list)
    confidence: float = 1.0
    raw_properties: dict[str, Any] = field(default_factory=dict)

    def center(self) -> tuple[int, int]:
        if self.clickable_x is not None and self.clickable_y is not None:
            return self.clickable_x, self.clickable_y
        return self.x + self.width // 2, self.y + self.height // 2

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw_properties", None)
        if self.raw_properties:
            d["raw_properties"] = self.raw_properties
        return d


def element_to_dict(elem: DetectedElement) -> dict:
    return elem.to_dict()


def dict_to_legacy_element(d: dict) -> dict:
    """Convert DetectedElement dict to legacy ui_automation format."""
    return {
        "name": d.get("name", ""),
        "role": d.get("role", ""),
        "x": d.get("x", 0),
        "y": d.get("y", 0),
        "width": d.get("width", 0),
        "height": d.get("height", 0),
        "value": d.get("value", ""),
        "automation_id": d.get("automation_id", ""),
        "class_name": d.get("class_name", ""),
        "framework_id": d.get("framework_id", ""),
        "visible": d.get("visible", True),
        "enabled": d.get("enabled", True),
        "backend": d.get("backend", "uia"),
        "patterns": d.get("patterns", []),
    }
