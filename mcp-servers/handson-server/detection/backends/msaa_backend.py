"""MSAA (IAccessible) detection backend via oleacc.dll."""
from __future__ import annotations

import sys
from typing import Optional

from detection.backends.base import DetectionBackend
from detection.element_model import DetectedElement

CHILDID_SELF = 0
OBJID_CLIENT = -4

# MSAA role constants (subset)
_ROLE_NAMES = {
    0x2B: "PushButton",
    0x2A: "Text",
    0x2C: "CheckBox",
    0x2D: "RadioButton",
    0x2E: "ComboBox",
    0x2F: "DropList",
    0x21: "Client",
    0x10: "Pane",
    0x24: "Table",
    0x22: "List",
    0x23: "ListItem",
    0x0C: "MenuItem",
    0x02: "MenuBar",
    0x09: "Window",
    0x2B: "Button",
}


def _get_oleacc():
    from ctypes import oledll, byref, POINTER
    from ctypes.wintypes import POINT
    from comtypes.automation import VARIANT
    from comtypes import IUnknown
    from comtypes.client import GetModule, wrap

    GetModule("oleacc.dll")
    from comtypes.gen.Accessibility import IAccessible  # noqa: F401

    def accessible_from_point(x, y):
        pacc = POINTER(IUnknown)()
        var = VARIANT()
        oledll.oleacc.AccessibleObjectFromPoint(POINT(x, y), byref(pacc), byref(var))
        child_id = var.value if isinstance(var.value, int) else 0
        return wrap(pacc), child_id

    def accessible_from_window(hwnd):
        from comtypes.gen.Accessibility import IAccessible
        pacc = POINTER(IAccessible)()
        oledll.oleacc.AccessibleObjectFromWindow(
            hwnd, OBJID_CLIENT, byref(IAccessible._iid_), byref(pacc)
        )
        return pacc

    return accessible_from_point, accessible_from_window


def _acc_to_element(acc, child_id: int, backend: str = "msaa") -> Optional[DetectedElement]:
    try:
        name = acc.accName(child_id) or ""
        role_val = acc.accRole(child_id)
        role = _ROLE_NAMES.get(role_val, f"Role_{role_val}")
        value = ""
        try:
            value = acc.accValue(child_id) or ""
        except Exception:
            pass
        x, y, w, h = 0, 0, 0, 0
        try:
            loc = acc.accLocation(child_id)
            if loc:
                x, y, w, h = int(loc[0]), int(loc[1]), int(loc[2]), int(loc[3])
        except Exception:
            pass
        state = 0
        try:
            state = acc.accState(child_id)
        except Exception:
            pass
        visible = not (state & 0x8000)  # STATE_SYSTEM_OFFSCREEN
        enabled = not (state & 0x1)  # STATE_SYSTEM_UNAVAILABLE
        return DetectedElement(
            name=str(name),
            role=role,
            x=x, y=y, width=w, height=h,
            value=str(value),
            backend=backend,
            visible=visible,
            enabled=enabled,
            raw_properties={"acc_state": state, "acc_role": role_val},
        )
    except Exception:
        return None


def _walk_accessible(acc, child_id: int, depth: int, max_depth: int, results: list):
    if depth > max_depth:
        return
    elem = _acc_to_element(acc, child_id)
    if elem:
        results.append((acc, child_id, elem))
    try:
        count = acc.accChildCount
    except Exception:
        count = 0
    for i in range(count):
        try:
            child = acc.accChild(i)
            if child is None:
                continue
            if hasattr(child, "accName"):
                _walk_accessible(child, CHILDID_SELF, depth + 1, max_depth, results)
            else:
                ce = _acc_to_element(acc, i + 1)
                if ce:
                    results.append((acc, i + 1, ce))
        except Exception:
            continue


def _resolve_hwnd(window_title: Optional[str]) -> int:
    if window_title:
        from tools.windows import do_list_windows, find_matching_window
        match = find_matching_window(window_title, do_list_windows())
        if match["window"] and match["window"].get("hwnd"):
            return match["window"]["hwnd"]
    from handson_platform.win32_backend import get_foreground_hwnd
    return get_foreground_hwnd()


class MSAABackend(DetectionBackend):
    name = "msaa"

    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            _get_oleacc()
            return True
        except Exception:
            return False

    def _get_tree(self, window_title: Optional[str], max_depth: int) -> list[DetectedElement]:
        hwnd = _resolve_hwnd(window_title)
        if not hwnd:
            return []
        _, accessible_from_window = _get_oleacc()
        acc = accessible_from_window(hwnd)
        raw: list = []
        _walk_accessible(acc, CHILDID_SELF, 0, max_depth, raw)
        return [e for _, _, e in raw]

    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 5,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> list[DetectedElement]:
        elements = self._get_tree(window_title, max_depth)
        role_lower = role.lower() if role else None
        out = []
        for e in elements:
            if not include_offscreen and not e.visible:
                continue
            if role_lower and role_lower not in (e.role or "").lower():
                continue
            if e.name or e.role not in ("Pane", "Client"):
                out.append(e)
        return out

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
        all_elems = self.list_elements(
            window_title=window_title, max_depth=10,
            include_offscreen=include_offscreen,
        )
        matches = []
        for e in all_elems:
            if name and name.lower() not in (e.name or "").lower():
                continue
            if role and role.lower() not in (e.role or "").lower():
                continue
            matches.append(e)
        if not matches:
            return []
        if index > 0:
            return [matches[min(index, len(matches) - 1)]]
        return matches

    def element_at_point(self, x: int, y: int) -> Optional[DetectedElement]:
        try:
            accessible_from_point, _ = _get_oleacc()
            acc, child_id = accessible_from_point(x, y)
            return _acc_to_element(acc, child_id)
        except Exception:
            return None
