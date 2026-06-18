"""UIA3 detection backend — pywinauto + comtypes direct access."""
from __future__ import annotations

import sys
from typing import Any, Optional

from detection.backends.base import DetectionBackend
from detection.element_model import DetectedElement

# UIA pattern IDs (subset)
_UIA_PATTERNS = {
    10000: "Invoke",
    10001: "Selection",
    10002: "Value",
    10003: "RangeValue",
    10004: "Scroll",
    10005: "ExpandCollapse",
    10010: "SelectionItem",
    10015: "Toggle",
    10017: "ScrollItem",
    10018: "LegacyIAccessible",
    10014: "Text",
}

_iuia = None


def _get_iuia():
    global _iuia
    if _iuia is None:
        from pywinauto.uia_defines import IUIA
        _iuia = IUIA()
    return _iuia


def _get_desktop():
    from pywinauto import Desktop
    return Desktop(backend="uia")


def _get_foreground_window(desktop):
    """Resolve the actual foreground window, not desktop.windows()[0]."""
    if sys.platform != "win32":
        windows = desktop.windows()
        return windows[0] if windows else None
    from handson_platform.win32_backend import get_foreground_hwnd
    from pywinauto.uia_element_info import UIAElementInfo
    hwnd = get_foreground_hwnd()
    if hwnd:
        try:
            return desktop.window(handle=hwnd)
        except Exception:
            pass
        try:
            info = UIAElementInfo(hwnd)
            from pywinauto.controls.uiawrapper import UIAWrapper
            return UIAWrapper(info)
        except Exception:
            pass
    windows = desktop.windows()
    return windows[0] if windows else None


def _find_window(desktop, window_title: str):
    from tools.windows import find_matching_window
    windows = []
    for win in desktop.windows():
        try:
            windows.append({"_obj": win, "title": win.window_text()})
        except Exception:
            continue
    result = find_matching_window(window_title, windows)
    return result["window"]["_obj"] if result["window"] else None


def _safe_get(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _get_patterns(elem) -> list[str]:
    patterns = []
    try:
        raw = elem.element_info.element
        iuia = _get_iuia().iuia
        for pid, pname in _UIA_PATTERNS.items():
            try:
                if raw.GetCurrentPattern(pid) is not None:
                    patterns.append(pname)
            except Exception:
                continue
    except Exception:
        pass
    return patterns


def _get_clickable_point(elem) -> tuple[Optional[int], Optional[int]]:
    try:
        from ctypes import byref
        from ctypes.wintypes import POINT
        pt = POINT()
        raw = elem.element_info.element
        if raw.GetClickablePoint(byref(pt)) != 0:
            return pt.x, pt.y
    except Exception:
        pass
    return None, None


def _pywinauto_to_element(elem, backend: str = "uia") -> Optional[DetectedElement]:
    try:
        info = elem.element_info
        rect = info.rectangle
        cx, cy = _get_clickable_point(elem)
        runtime_id = ""
        try:
            rid = info.runtime_id
            if rid:
                runtime_id = str(list(rid)) if hasattr(rid, "__iter__") else str(rid)
        except Exception:
            pass

        aria_role = ""
        aria_properties = ""
        try:
            raw = info.element
            aria_role = _safe_get(lambda: raw.CurrentAriaRole, "") or ""
            aria_properties = _safe_get(lambda: raw.CurrentAriaProperties, "") or ""
        except Exception:
            pass

        has_focus = False
        is_kbf = False
        enabled = True
        try:
            raw = info.element
            has_focus = bool(_safe_get(lambda: raw.CurrentHasKeyboardFocus, False))
            is_kbf = bool(_safe_get(lambda: raw.CurrentIsKeyboardFocusable, False))
            enabled = bool(_safe_get(lambda: raw.CurrentIsEnabled, True))
        except Exception:
            pass

        return DetectedElement(
            name=info.name or "",
            role=info.control_type or "",
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            value=getattr(info, "rich_text", "") or "",
            backend=backend,
            automation_id=info.automation_id or "",
            class_name=info.class_name or "",
            framework_id=info.framework_id or "",
            runtime_id=runtime_id,
            process_id=info.process_id or 0,
            hwnd=info.handle or 0,
            enabled=enabled,
            visible=bool(info.visible),
            has_focus=has_focus,
            is_keyboard_focusable=is_kbf,
            access_key=_safe_get(lambda: info.element.CurrentAccessKey, "") or "",
            help_text=_safe_get(lambda: info.element.CurrentHelpText, "") or "",
            localized_control_type=_safe_get(
                lambda: info.element.CurrentLocalizedControlType, ""
            ) or "",
            aria_role=aria_role,
            aria_properties=aria_properties,
            clickable_x=cx,
            clickable_y=cy,
            patterns=_get_patterns(elem),
        )
    except Exception:
        return None


def _walk_tree_comtypes(root_element, tree_mode: str = "control", max_depth: int = 100):
    """Walk UIA tree using Raw/Content/Control view walkers."""
    iuia = _get_iuia().iuia
    if tree_mode == "raw":
        walker = iuia.RawViewWalker
    elif tree_mode == "content":
        walker = iuia.ContentViewWalker
    else:
        walker = iuia.ControlViewWalker

    from pywinauto.uia_element_info import UIAElementInfo
    from pywinauto.controls.uiawrapper import UIAWrapper

    results = []

    def walk(elem, depth):
        if depth > max_depth:
            return
        try:
            wrapper = UIAWrapper(UIAElementInfo(elem))
            results.append(wrapper)
        except Exception:
            pass
        try:
            child = walker.GetFirstChildElement(elem)
            while child:
                walk(child, depth + 1)
                child = walker.GetNextSiblingElement(child)
        except Exception:
            pass

    walk(root_element, 0)
    return results


def _resolve_window(desktop, window_title: Optional[str]):
    if window_title:
        return _find_window(desktop, window_title)
    return _get_foreground_window(desktop)


def _element_useful(d: DetectedElement, include_offscreen: bool) -> bool:
    if not include_offscreen and not d.visible:
        return False
    if d.name or d.role not in ("", "Pane", "Group", "Custom"):
        return True
    if d.automation_id or d.class_name:
        return True
    return False


def _matches(
    d: DetectedElement,
    name: Optional[str],
    role: Optional[str],
    automation_id: Optional[str],
    class_name: Optional[str],
) -> bool:
    if name and name.lower() not in (d.name or "").lower():
        return False
    if role and role.lower() != (d.role or "").lower():
        return False
    if automation_id and automation_id != d.automation_id:
        return False
    if class_name and class_name.lower() not in (d.class_name or "").lower():
        return False
    return True


class UIABackend(DetectionBackend):
    name = "uia"

    def is_available(self) -> bool:
        return sys.platform == "win32"

    def _collect_descendants(
        self, window, tree_mode: str, max_depth: int, role: Optional[str]
    ):
        if tree_mode != "control":
            try:
                raw = window.element_info.element
                depth = 100 if role else max_depth
                return _walk_tree_comtypes(raw, tree_mode, depth)
            except Exception:
                pass
        if role:
            return window.descendants()
        return window.descendants(depth=max_depth)

    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 5,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> list[DetectedElement]:
        if not self.is_available():
            return []
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title)
        if not window:
            return []
        try:
            descendants = self._collect_descendants(window, tree_mode, max_depth, role)
        except Exception:
            return []

        role_lower = role.lower() if role else None
        elements = []
        for elem in descendants:
            d = _pywinauto_to_element(elem)
            if not d:
                continue
            if role_lower and (d.role or "").lower() != role_lower:
                continue
            if not _element_useful(d, include_offscreen):
                continue
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
        all_elems = self.list_elements(
            window_title=window_title,
            max_depth=100 if (role or automation_id or class_name) else 5,
            role=role,
            tree_mode=tree_mode,
            include_offscreen=include_offscreen,
        )
        matches = [
            d for d in all_elems
            if _matches(d, name, role, automation_id, class_name)
        ]
        if not matches:
            return []
        if index > 0:
            idx = min(index, len(matches) - 1)
            return [matches[idx]]
        return matches

    def element_at_point(self, x: int, y: int) -> Optional[DetectedElement]:
        if not self.is_available():
            return None
        try:
            from pywinauto.uia_element_info import UIAElementInfo
            from pywinauto.controls.uiawrapper import UIAWrapper
            info = UIAElementInfo.from_point(x, y)
            wrapper = UIAWrapper(info)
            return _pywinauto_to_element(wrapper)
        except Exception:
            return None

    def get_properties(self, element: DetectedElement) -> dict:
        d = element.to_dict()
        d["raw_properties"] = element.raw_properties or {}
        return d

    def _find_raw_element(self, name: str = "", role: str = "", window_title: Optional[str] = None):
        desktop = _get_desktop()
        window = _resolve_window(desktop, window_title)
        if not window:
            return None, None
        for elem in window.descendants():
            d = _pywinauto_to_element(elem)
            if not d:
                continue
            if name and name.lower() not in (d.name or "").lower():
                continue
            if role and role.lower() not in (d.role or "").lower():
                continue
            return elem, d
        return None, None

    def invoke_element_by_name(
        self,
        name: str,
        role: str = "",
        window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            elem, _ = self._find_raw_element(name=name, role=role, window_title=window_title)
            if not elem:
                return {"success": False, "error": "element not found"}
            pattern = get_elem_interface(elem.element_info.element, "Invoke")
            pattern.Invoke()
            return {"success": True, "method": "InvokePattern"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def expand_element(
        self,
        name: str = "",
        role: str = "MenuItem",
        window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            elem, _ = self._find_raw_element(name=name, role=role, window_title=window_title)
            if not elem:
                return {"success": False, "error": "element not found"}
            pattern = get_elem_interface(elem.element_info.element, "ExpandCollapse")
            pattern.Expand()
            return {"success": True, "method": "ExpandCollapse.Expand"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def collapse_element(
        self,
        name: str = "",
        role: str = "",
        window_title: Optional[str] = None,
    ) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            elem, _ = self._find_raw_element(name=name, role=role, window_title=window_title)
            if not elem:
                return {"success": False, "error": "element not found"}
            pattern = get_elem_interface(elem.element_info.element, "ExpandCollapse")
            pattern.Collapse()
            return {"success": True, "method": "ExpandCollapse.Collapse"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def invoke_element(self, element: DetectedElement) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            matches = self.find_elements(
                automation_id=element.automation_id or None,
                name=element.name or None,
                role=element.role or None,
                include_offscreen=True,
            )
            if not matches:
                return {"success": False, "error": "Element not found for invoke"}
            desktop = _get_desktop()
            window = _resolve_window(desktop, None)
            for elem in window.descendants():
                d = _pywinauto_to_element(elem)
                if d and d.name == element.name and d.role == element.role:
                    if element.automation_id and d.automation_id != element.automation_id:
                        continue
                    pattern = get_elem_interface(elem.element_info.element, "Invoke")
                    pattern.Invoke()
                    return {"success": True, "method": "InvokePattern"}
            return {"success": False, "error": "InvokePattern not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_element_value(self, element: DetectedElement, value: str) -> dict:
        try:
            from pywinauto.uia_defines import get_elem_interface
            desktop = _get_desktop()
            window = _resolve_window(desktop, None)
            for elem in window.descendants():
                d = _pywinauto_to_element(elem)
                if not d:
                    continue
                if element.automation_id and d.automation_id == element.automation_id:
                    pattern = get_elem_interface(elem.element_info.element, "Value")
                    pattern.SetValue(value)
                    return {"success": True, "method": "ValuePattern"}
                if element.name and d.name == element.name and d.role == element.role:
                    pattern = get_elem_interface(elem.element_info.element, "Value")
                    pattern.SetValue(value)
                    return {"success": True, "method": "ValuePattern"}
            return {"success": False, "error": "ValuePattern not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def ensure_chromium_accessibility(self, window_title: Optional[str] = None) -> dict:
        """Subscribe to UIA events to encourage Chromium to expose its tree."""
        try:
            from tools.framework_detect import do_detect_framework
            fw = do_detect_framework(window_title)
            if fw.get("framework") not in ("electron", "chromium_browser"):
                return {"triggered": False, "reason": "not chromium"}
            elements = self.list_elements(window_title=window_title, max_depth=3)
            named = [e for e in elements if e.name.strip()]
            if len(named) >= 5:
                return {"triggered": False, "reason": "tree already populated"}
            iuia = _get_iuia().iuia
            desktop = _get_desktop()
            window = _resolve_window(desktop, window_title)
            if not window:
                return {"triggered": False, "error": "window not found"}
            # Register brief structure-changed handler to wake renderer bridge
            try:
                handler = iuia.CreateEventHandler()
                iuia.iuia.AddStructureChangedEventHandler(
                    window.element_info.element,
                    1,  # TreeScope_Subtree
                    None,
                    handler,
                )
            except Exception:
                pass
            return {
                "triggered": True,
                "hint": "Relaunch with --force-renderer-accessibility if tree stays empty",
                "named_elements": len(named),
            }
        except Exception as e:
            return {"triggered": False, "error": str(e)}


def get_uia_backend() -> UIABackend:
    return UIABackend()
