"""Win32 HWND backend using pywinauto win32 API."""
from __future__ import annotations

import sys
from typing import Optional

from detection.backends.base import DetectionBackend
from detection.element_model import DetectedElement


def _get_desktop():
    from pywinauto import Desktop
    return Desktop(backend="win32")


def _resolve_window(desktop, window_title: Optional[str]):
    if window_title:
        from tools.windows import find_matching_window
        windows = []
        for win in desktop.windows():
            try:
                windows.append({"_obj": win, "title": win.window_text()})
            except Exception:
                continue
        result = find_matching_window(window_title, windows)
        return result["window"]["_obj"] if result["window"] else None
    from handson_platform.win32_backend import get_foreground_hwnd
    hwnd = get_foreground_hwnd()
    if hwnd:
        try:
            return desktop.window(handle=hwnd)
        except Exception:
            pass
    windows = desktop.windows()
    return windows[0] if windows else None


def _win32_to_element(elem) -> Optional[DetectedElement]:
    try:
        rect = elem.rectangle()
        class_name = elem.class_name() if callable(getattr(elem, "class_name", None)) else ""
        if not callable(getattr(elem, "class_name", None)):
            class_name = getattr(elem, "class_name", "") or ""
        name = ""
        try:
            name = elem.window_text()
        except Exception:
            pass
        control_id = 0
        try:
            control_id = elem.control_id()
        except Exception:
            pass
        role = class_name or "Control"
        return DetectedElement(
            name=name or "",
            role=role,
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            backend="win32",
            class_name=class_name,
            hwnd=elem.handle if hasattr(elem, "handle") else 0,
            raw_properties={"control_id": control_id},
        )
    except Exception:
        return None


class Win32HwndBackend(DetectionBackend):
    name = "win32"

    def is_available(self) -> bool:
        return sys.platform == "win32"

    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 5,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> list[DetectedElement]:
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title)
        if not window:
            return []
        try:
            descendants = window.descendants()
        except Exception:
            return []
        elements = []
        role_lower = role.lower() if role else None
        for elem in descendants:
            d = _win32_to_element(elem)
            if not d:
                continue
            if role_lower and role_lower not in (d.class_name or "").lower():
                continue
            if d.name or d.class_name:
                elements.append(d)
        return elements

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
        all_elems = self.list_elements(window_title=window_title, max_depth=10)
        matches = []
        for e in all_elems:
            if name and name.lower() not in (e.name or "").lower():
                continue
            if class_name and class_name.lower() not in (e.class_name or "").lower():
                continue
            if role and role.lower() not in (e.role or "").lower():
                continue
            matches.append(e)
        if not matches:
            return []
        if index > 0:
            return [matches[min(index, len(matches) - 1)]]
        return matches
