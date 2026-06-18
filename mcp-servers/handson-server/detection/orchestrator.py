"""Multi-backend detection orchestrator."""
from __future__ import annotations

import sys
import time
from typing import Optional

from detection.element_model import DetectedElement, dict_to_legacy_element
from detection.backends.base import DetectionBackend
from detection.layers.layered_detector import LayeredDetector, LocatorQuery, ResolveOptions

_orchestrator: Optional["DetectionOrchestrator"] = None
_tree_cache: dict[str, tuple[float, list[DetectedElement]]] = {}
_CACHE_TTL = 2.0


class DetectionOrchestrator:
    """Route detection requests across backends by framework and fallback chain."""

    def __init__(self):
        self._backends: dict[str, DetectionBackend] = {}
        self._init_backends()
        self._layered = LayeredDetector(self)

    def _init_backends(self):
        if sys.platform == "win32":
            from detection.backends.uia_backend import UIABackend
            self._backends["uia"] = UIABackend()
            try:
                from detection.backends.msaa_backend import MSAABackend
                self._backends["msaa"] = MSAABackend()
            except ImportError:
                pass
            try:
                from detection.backends.win32_hwnd_backend import Win32HwndBackend
                self._backends["win32"] = Win32HwndBackend()
            except ImportError:
                pass
            try:
                from detection.backends.jab_backend import JABBackend
                self._backends["jab"] = JABBackend()
            except ImportError:
                pass
            try:
                from detection.backends.flaui_backend import FlaUIBackend
                self._backends["flaui"] = FlaUIBackend()
            except ImportError:
                pass

    def _backend_order(self, window_title: Optional[str] = None) -> list[str]:
        order = ["uia"]
        try:
            from tools.framework_detect import do_detect_framework
            fw = do_detect_framework(window_title).get("framework", "unknown")
            if fw == "java_swing":
                order = ["jab", "uia"]
            elif fw in ("win32", "mfc"):
                order = ["uia", "msaa", "win32"]
            elif fw == "winforms":
                order = ["flaui", "uia", "msaa"]
            elif fw == "wpf":
                order = ["uia", "flaui", "msaa"]
            elif fw == "gtk":
                order = []  # OCR/visual handled by layered detector
            elif fw in ("electron", "chromium_browser"):
                order = ["uia", "flaui", "msaa"]
            elif fw == "java_fx":
                order = ["uia", "jab"]
            else:
                order = ["uia", "flaui", "msaa", "win32", "jab"]
        except Exception:
            order = ["uia", "msaa", "win32", "jab", "flaui"]
        return [b for b in order if b in self._backends and self._backends[b].is_available()]

    def list_elements(
        self,
        window_title: Optional[str] = None,
        max_depth: int = 5,
        role: Optional[str] = None,
        tree_mode: str = "control",
        include_offscreen: bool = False,
        backend: Optional[str] = None,
    ) -> dict:
        cache_key = f"{window_title}|{max_depth}|{role}|{tree_mode}|{include_offscreen}|{backend}"
        now = time.monotonic()
        if cache_key in _tree_cache:
            ts, cached = _tree_cache[cache_key]
            if now - ts < _CACHE_TTL:
                return {
                    "elements": [dict_to_legacy_element(e.to_dict()) for e in cached],
                    "count": len(cached),
                    "backend_used": backend or "cache",
                }

        backends = [backend] if backend else self._backend_order(window_title)
        last_error = ""
        for bname in backends:
            b = self._backends.get(bname)
            if not b:
                continue
            try:
                elements = b.list_elements(
                    window_title=window_title,
                    max_depth=max_depth,
                    role=role,
                    tree_mode=tree_mode,
                    include_offscreen=include_offscreen,
                )
                if elements:
                    _tree_cache[cache_key] = (now, elements)
                    return {
                        "elements": [dict_to_legacy_element(e.to_dict()) for e in elements],
                        "count": len(elements),
                        "backend_used": bname,
                    }
            except Exception as e:
                last_error = str(e)
        return {"elements": [], "count": 0, "error": last_error or "no elements found"}

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
    ) -> dict:
        backends = self._backend_order(window_title)
        all_matches: list[DetectedElement] = []
        backend_used = ""
        for bname in backends:
            b = self._backends.get(bname)
            if not b:
                continue
            try:
                matches = b.find_elements(
                    name=name,
                    role=role,
                    automation_id=automation_id,
                    class_name=class_name,
                    window_title=window_title,
                    tree_mode=tree_mode,
                    include_offscreen=include_offscreen,
                    index=0,
                )
                if matches:
                    all_matches = matches
                    backend_used = bname
                    break
            except Exception:
                continue

        if not all_matches:
            # OCR fallback handled by smart_find caller
            return {"found": False, "elements": [], "backend_used": ""}

        if index > 0:
            idx = min(index, len(all_matches) - 1)
            selected = [all_matches[idx]]
        else:
            selected = all_matches

        return {
            "found": True,
            "elements": [dict_to_legacy_element(e.to_dict()) for e in selected],
            "backend_used": backend_used,
        }

    def element_at_point(self, x: int, y: int, window_title: Optional[str] = None) -> dict:
        for bname in self._backend_order(window_title):
            b = self._backends.get(bname)
            if not b:
                continue
            elem = b.element_at_point(x, y)
            if elem:
                return {
                    "found": True,
                    "element": dict_to_legacy_element(elem.to_dict()),
                    "backend_used": bname,
                }
        return {"found": False, "error": f"No element at ({x}, {y})"}

    def get_element_properties(
        self,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        window_title: Optional[str] = None,
    ) -> dict:
        elem = None
        backend_used = ""
        if x is not None and y is not None:
            r = self.element_at_point(x, y)
            if r.get("found"):
                return {"found": True, "properties": r["element"], "backend_used": r["backend_used"]}
        for bname in self._backend_order(window_title):
            b = self._backends.get(bname)
            if not b:
                continue
            matches = b.find_elements(
                name=name,
                automation_id=automation_id,
                window_title=window_title,
                include_offscreen=True,
            )
            if matches:
                elem = matches[0]
                backend_used = bname
                break
        if not elem:
            return {"found": False, "error": "Element not found"}
        props = b.get_properties(elem) if (b := self._backends.get(backend_used)) else elem.to_dict()
        return {"found": True, "properties": props, "backend_used": backend_used}

    def detection_health(self, window_title: Optional[str] = None) -> dict:
        health = {"backends": {}, "framework": "unknown", "recommended_order": []}
        try:
            from tools.framework_detect import do_detect_framework
            health["framework"] = do_detect_framework(window_title).get("framework", "unknown")
        except Exception:
            pass
        health["recommended_order"] = self._backend_order(window_title)
        for name, backend in self._backends.items():
            available = backend.is_available()
            count = 0
            if available:
                try:
                    elems = backend.list_elements(window_title=window_title, max_depth=3)
                    count = len(elems)
                except Exception:
                    count = -1
            health["backends"][name] = {"available": available, "element_count": count}
        return health

    def smart_find(
        self,
        name: str,
        role: Optional[str] = None,
        window_title: Optional[str] = None,
        index: int = 0,
        repo_path: Optional[str] = None,
        agentic: bool = False,
        remember: bool = True,
        highlight: bool = False,
    ) -> dict:
        query = LocatorQuery(
            name=name,
            role=role,
            window_title=window_title,
            index=index,
            repo_path=repo_path,
        )
        opts = ResolveOptions(agentic=agentic, remember=remember, highlight=highlight)
        result = self._layered.resolve(query, opts)
        if result.found and remember and result.elements:
            try:
                from detection.object_snapshot import capture_object_snapshot
                from tools.framework_detect import do_detect_framework
                fw = do_detect_framework(window_title)
                capture_object_snapshot(
                    result.elements[0],
                    window_title=window_title,
                    repo_path=repo_path,
                    app_name=fw.get("process_name") or fw.get("exe_name") or "foreground",
                    exe_path=fw.get("exe_path", ""),
                    highlight=highlight,
                )
            except Exception:
                pass
        return result.to_dict()

    def build_detection_context(
        self,
        name: str = "",
        window_title: Optional[str] = None,
    ) -> dict:
        query = LocatorQuery(name=name or None, window_title=window_title)
        return self._layered.build_detection_context(query)


def get_orchestrator() -> DetectionOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DetectionOrchestrator()
    return _orchestrator
