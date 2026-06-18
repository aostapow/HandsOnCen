"""Java Access Bridge detection backend via pyjab."""
from __future__ import annotations

import os
import sys
from typing import Optional

from detection.backends.base import DetectionBackend
from detection.element_model import DetectedElement

_jab_driver = None


def _jab_available() -> bool:
    if sys.platform != "win32":
        return False
    if not (os.environ.get("JAVA_HOME") or os.environ.get("JAB_HOME")):
        return False
    try:
        import pyjab  # noqa: F401
        return True
    except ImportError:
        return False


def _get_jab_driver(window_title: str):
    global _jab_driver
    from pyjab.jabdriver import JABDriver
    if _jab_driver is None:
        _jab_driver = JABDriver(window_title)
    return _jab_driver


def _jab_elem_to_detected(jab_elem) -> Optional[DetectedElement]:
    try:
        info = jab_elem.get_element_information()
        bounds = info.get("bounds", {})
        return DetectedElement(
            name=info.get("name", "") or "",
            role=info.get("role", "") or "",
            x=bounds.get("x", 0),
            y=bounds.get("y", 0),
            width=bounds.get("width", 0),
            height=bounds.get("height", 0),
            value=info.get("text", "") or "",
            backend="jab",
            enabled=info.get("enabled", True),
            visible=info.get("visible", True),
            raw_properties=info,
        )
    except Exception:
        return None


def check_java_bridge() -> dict:
    """Diagnostic: verify JAB prerequisites."""
    result = {
        "available": False,
        "java_home": os.environ.get("JAVA_HOME", ""),
        "jab_home": os.environ.get("JAB_HOME", ""),
        "pyjab_installed": False,
        "hints": [],
    }
    try:
        import pyjab  # noqa: F401
        result["pyjab_installed"] = True
    except ImportError:
        result["hints"].append("pip install pyjab")
        return result
    if not (result["java_home"] or result["jab_home"]):
        result["hints"].append("Set JAVA_HOME or JAB_HOME to your JDK/JRE path")
        result["hints"].append('Run: "%JAVA_HOME%\\bin\\jabswitch" -enable')
        return result
    jabswitch = os.path.join(
        result["java_home"] or result["jab_home"], "bin", "jabswitch.exe"
    )
    if os.path.isfile(jabswitch):
        result["jabswitch_path"] = jabswitch
        result["hints"].append("Ensure jabswitch -enable has been run and Java apps restarted")
    result["available"] = True
    return result


class JABBackend(DetectionBackend):
    name = "jab"

    def is_available(self) -> bool:
        return _jab_available()

    def _title(self, window_title: Optional[str]) -> str:
        if window_title:
            return window_title
        from handson_platform.win32_backend import get_foreground_title
        return get_foreground_title()

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
        try:
            driver = _get_jab_driver(self._title(window_title))
            root = driver.root_element
            elements = []
            self._walk_jab(root, elements, 0, max_depth, role)
            return elements
        except Exception:
            return []

    def _walk_jab(self, elem, results, depth, max_depth, role_filter):
        if depth > max_depth:
            return
        d = _jab_elem_to_detected(elem)
        if d:
            if not role_filter or role_filter.lower() in (d.role or "").lower():
                if d.name or d.role:
                    results.append(d)
        try:
            for child in elem.children:
                self._walk_jab(child, results, depth + 1, max_depth, role_filter)
        except Exception:
            pass

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
        if not self.is_available():
            return []
        try:
            driver = _get_jab_driver(self._title(window_title))
            if name:
                try:
                    found = driver.find_element_by_name(name)
                    d = _jab_elem_to_detected(found)
                    return [d] if d else []
                except Exception:
                    pass
            all_elems = self.list_elements(window_title=window_title, max_depth=10, role=role)
            matches = [
                e for e in all_elems
                if (not name or name.lower() in (e.name or "").lower())
                and (not role or role.lower() in (e.role or "").lower())
            ]
            if not matches:
                return []
            if index > 0:
                return [matches[min(index, len(matches) - 1)]]
            return matches
        except Exception:
            return []
