"""UI Automation tools -- find and click elements by name/role.

Uses multi-backend detection (UIA, MSAA, Win32, JAB, FlaUI) via detection.orchestrator.
Falls back to OCR and visual detection through smart_find.
"""
from __future__ import annotations

import hashlib
import sys
from difflib import SequenceMatcher
from typing import Optional

from tools.input_tools import do_click


def _orch():
    from detection.orchestrator import get_orchestrator
    return get_orchestrator()


def _legacy_element(elem: dict) -> dict:
    """Ensure legacy keys exist for callers expecting old format."""
    return {
        "name": elem.get("name", ""),
        "role": elem.get("role", ""),
        "x": elem.get("x", 0),
        "y": elem.get("y", 0),
        "width": elem.get("width", 0),
        "height": elem.get("height", 0),
        "value": elem.get("value", ""),
        "automation_id": elem.get("automation_id", ""),
        "class_name": elem.get("class_name", ""),
        "framework_id": elem.get("framework_id", ""),
        "visible": elem.get("visible", True),
        "enabled": elem.get("enabled", True),
        "backend": elem.get("backend", "uia"),
        "patterns": elem.get("patterns", []),
    }


def _do_find_element_darwin(
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    automation_id: Optional[str] = None,
    class_name: Optional[str] = None,
    tree_mode: str = "control",
    include_offscreen: bool = False,
    index: int = 0,
) -> dict:
    from handson_platform.darwin_backend import (
        ax_get_frontmost_app,
        ax_get_app_for_title,
        ax_find_elements,
    )

    if window_title:
        root = ax_get_app_for_title(window_title)
        if root is None:
            return {"found": False, "elements": [], "error": f"Window '{window_title}' not found"}
    else:
        root = ax_get_frontmost_app()
        if root is None:
            return {"found": False, "elements": [], "error": "No frontmost application found"}

    matches = ax_find_elements(root, name=name, role=role)
    if not matches:
        return {"found": False, "elements": []}
    if index > 0:
        idx = min(index, len(matches) - 1)
        return {"found": True, "elements": [matches[idx]]}
    return {"found": True, "elements": matches}


def _do_list_elements_darwin(
    window_title: Optional[str] = None,
    max_depth: int = 5,
    role: Optional[str] = None,
) -> dict:
    from handson_platform.darwin_backend import (
        ax_get_frontmost_app,
        ax_get_app_for_title,
        ax_find_elements,
    )

    if window_title:
        root = ax_get_app_for_title(window_title)
        if root is None:
            return {"elements": [], "error": f"Window '{window_title}' not found"}
    else:
        root = ax_get_frontmost_app()
        if root is None:
            return {"elements": [], "error": "No frontmost application found"}

    depth = 100 if role else max_depth
    all_elements = ax_find_elements(root, role=role, max_depth=depth)
    return {"elements": all_elements, "count": len(all_elements)}


def do_find_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    automation_id: Optional[str] = None,
    class_name: Optional[str] = None,
    tree_mode: str = "control",
    include_offscreen: bool = False,
) -> dict:
    if sys.platform == "darwin":
        return _do_find_element_darwin(
            name, role, window_title, automation_id, class_name, tree_mode, include_offscreen, index,
        )

    result = _orch().find_elements(
        name=name,
        role=role,
        automation_id=automation_id,
        class_name=class_name,
        window_title=window_title,
        tree_mode=tree_mode,
        include_offscreen=include_offscreen,
        index=index,
    )
    if not result.get("found"):
        return {"found": False, "elements": [], "error": result.get("error", "")}
    return {
        "found": True,
        "elements": [_legacy_element(e) for e in result["elements"]],
        "backend_used": result.get("backend_used", "uia"),
    }


def do_list_elements(
    window_title: Optional[str] = None,
    max_depth: int = 5,
    role: Optional[str] = None,
    tree_mode: str = "control",
    include_offscreen: bool = False,
) -> dict:
    if sys.platform == "darwin":
        return _do_list_elements_darwin(window_title, max_depth, role)

    return _orch().list_elements(
        window_title=window_title,
        max_depth=max_depth,
        role=role,
        tree_mode=tree_mode,
        include_offscreen=include_offscreen,
    )


def do_element_at_point(x: int, y: int) -> dict:
    if sys.platform == "darwin":
        return {"found": False, "error": "element_at_point not implemented on macOS yet"}
    return _orch().element_at_point(x, y)


def do_get_element_properties(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    window_title: Optional[str] = None,
) -> dict:
    if sys.platform == "darwin":
        return {"found": False, "error": "get_element_properties not implemented on macOS yet"}
    return _orch().get_element_properties(
        name=name,
        automation_id=automation_id,
        x=x,
        y=y,
        window_title=window_title,
    )


def do_invoke_element(
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> dict:
    if sys.platform != "win32":
        return {"success": False, "error": "invoke_element is Windows-only"}
    from detection.backends.uia_backend import get_uia_backend
    from detection.element_model import DetectedElement
    matches = do_find_element(
        name=name, automation_id=automation_id, window_title=window_title, include_offscreen=True,
    )
    if not matches.get("found"):
        return {"success": False, "error": "Element not found"}
    e = matches["elements"][0]
    elem = DetectedElement(
        name=e["name"], role=e["role"], automation_id=e.get("automation_id", ""),
    )
    return get_uia_backend().invoke_element(elem)


def do_set_element_value(
    value: str,
    name: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
) -> dict:
    if sys.platform != "win32":
        return {"success": False, "error": "set_element_value is Windows-only"}
    from detection.backends.uia_backend import get_uia_backend
    from detection.element_model import DetectedElement
    matches = do_find_element(
        name=name, automation_id=automation_id, window_title=window_title, include_offscreen=True,
    )
    if not matches.get("found"):
        return {"success": False, "error": "Element not found"}
    e = matches["elements"][0]
    elem = DetectedElement(
        name=e["name"], role=e["role"], automation_id=e.get("automation_id", ""),
    )
    return get_uia_backend().set_element_value(elem, value)


def _fuzzy_find_nearest(
    name: Optional[str],
    role: Optional[str],
    window_title: Optional[str],
) -> Optional[dict]:
    all_result = do_list_elements(window_title=window_title, role=role)
    candidates = all_result.get("elements", [])
    if not candidates:
        return None

    best = None
    best_confidence = 0.0
    best_method = "none"

    for elem in candidates:
        confidence = 0.0
        method = "role_only"

        if name and elem.get("name"):
            ratio = SequenceMatcher(None, name.lower(), elem["name"].lower()).ratio()
            if ratio >= 0.6:
                confidence = 0.5 + (ratio * 0.4)
                method = "fuzzy_name"

        if confidence == 0.0 and role:
            confidence = 0.4
            method = "role_only"

        if confidence > best_confidence:
            best_confidence = confidence
            best = elem
            best_method = method

    if best is None:
        return None

    return {
        "element": best,
        "confidence": round(best_confidence, 2),
        "match_method": best_method,
    }


def _click_coords(elem: dict) -> tuple[int, int]:
    cx = elem.get("clickable_x")
    cy = elem.get("clickable_y")
    if cx is not None and cy is not None:
        return int(cx), int(cy)
    return elem["x"] + elem["width"] // 2, elem["y"] + elem["height"] // 2


def do_click_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    automation_id: Optional[str] = None,
) -> dict:
    result = do_find_element(
        name=name, role=role, window_title=window_title,
        index=index, automation_id=automation_id,
    )
    if result["found"]:
        idx = min(index, len(result["elements"]) - 1)
        elem = result["elements"][idx]
        center_x, center_y = _click_coords(elem)
        click_result = do_click(center_x, center_y)
        out = {
            "success": True,
            "element": elem,
            "clicked_at": {"x": center_x, "y": center_y},
            "backend_used": result.get("backend_used", "uia"),
        }
        if "navigation_warning" in click_result:
            out["navigation_warning"] = click_result["navigation_warning"]
        return out

    nearest = _fuzzy_find_nearest(name=name, role=role, window_title=window_title)
    if nearest is None:
        return {"success": False, "error": f"Element not found: name={name}, role={role}"}

    if nearest["confidence"] >= 0.7:
        elem = nearest["element"]
        center_x, center_y = _click_coords(elem)
        click_result = do_click(center_x, center_y)
        out = {
            "success": True,
            "fallback": True,
            "confidence": nearest["confidence"],
            "match_method": nearest["match_method"],
            "element": elem,
            "clicked_at": {"x": center_x, "y": center_y},
            "note": (
                f"Exact match for '{name}' not found. Clicked nearest: "
                f"'{elem['name']}' ({nearest['match_method']}, confidence={nearest['confidence']})"
            ),
        }
        if "navigation_warning" in click_result:
            out["navigation_warning"] = click_result["navigation_warning"]
        return out

    elem = nearest["element"]
    cx, cy = _click_coords(elem)
    return {
        "success": False,
        "nearest": {
            "element": elem,
            "confidence": nearest["confidence"],
            "match_method": nearest["match_method"],
        },
        "error": (
            f"Exact match for '{name}' not found. "
            f"Nearest: '{elem['name']}' ({nearest['match_method']}, confidence={nearest['confidence']}). "
            f"Confidence too low to auto-click (threshold=0.7). "
            f"Click at ({cx}, {cy}) to target it manually."
        ),
    }


def do_get_focused_element() -> dict:
    if sys.platform == "darwin":
        from handson_platform.darwin_backend import ax_get_focused_element
        return ax_get_focused_element()

    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        focused = desktop.get_focus()
        from detection.backends.uia_backend import _pywinauto_to_element
        elem = _pywinauto_to_element(focused)
        if elem:
            return {"found": True, "element": _legacy_element(elem.to_dict())}
        return {"found": False, "error": "Focused element has no accessible info"}
    except Exception as e:
        return {"found": False, "error": str(e)}


def do_smart_find(
    name: str,
    role: Optional[str] = None,
    window_title: Optional[str] = None,
    index: int = 0,
    repo_path: Optional[str] = None,
    agentic: bool = False,
    remember: bool = True,
    highlight: bool = False,
) -> dict:
    if sys.platform == "darwin":
        try:
            uia_result = do_find_element(name=name, role=role, window_title=window_title, index=index)
            if uia_result.get("found") and uia_result["elements"]:
                return {"found": True, "method": "ax", "elements": uia_result["elements"]}
        except Exception:
            pass
        try:
            from tools.ocr import do_find_text
            ocr_result = do_find_text(name, window_title=window_title)
            if ocr_result["matches"]:
                elements = [{
                    "name": m["text"], "role": "text",
                    "x": m["x"], "y": m["y"],
                    "width": m["width"], "height": m["height"],
                    "value": "", "backend": "ocr",
                } for m in ocr_result["matches"]]
                return {"found": True, "method": "ocr", "elements": elements}
        except Exception:
            pass
        return {"found": False, "elements": [], "error": f"'{name}' not found"}

    return _orch().smart_find(
        name=name,
        role=role,
        window_title=window_title,
        index=index,
        repo_path=repo_path,
        agentic=agentic,
        remember=remember,
        highlight=highlight,
    )


def do_repo_find(
    repo_path: str,
    window_title: Optional[str] = None,
    highlight: bool = False,
) -> dict:
    parts = repo_path.split("/", 1)
    name = parts[1] if len(parts) == 2 else repo_path
    return do_smart_find(
        name=name,
        window_title=window_title,
        repo_path=repo_path,
        remember=True,
        highlight=highlight,
    )


def do_repo_list(window_title: Optional[str] = None) -> dict:
    from detection.object_repository import list_objects, load_repo
    from tools.framework_detect import do_detect_framework
    fw = do_detect_framework(window_title)
    app_name = fw.get("process_name") or fw.get("exe_name") or "foreground"
    repo = load_repo(app_name, fw.get("exe_path", ""))
    win_key = None
    if window_title:
        for k, w in repo.get("windows", {}).items():
            if window_title.lower() in k.lower():
                win_key = k
                break
    return {"objects": list_objects(repo, win_key), "app_id": repo["app_id"]}


def do_build_detection_context(name: str = "", window_title: Optional[str] = None) -> dict:
    if sys.platform == "darwin":
        return {"error": "agentic context is Windows-only for now"}
    return _orch().build_detection_context(name=name, window_title=window_title)


def do_ui_fingerprint(
    window_title: Optional[str] = None,
    max_elements: int = 20,
) -> dict:
    result = do_list_elements(window_title=window_title, max_depth=3)
    elements = result.get("elements", [])[:max_elements]

    parts = []
    for elem in elements:
        parts.append(f"{elem.get('role', '')}|{elem.get('name', '')}|{elem['x']}|{elem['y']}")
    fingerprint_str = "\n".join(sorted(parts))

    hash_hex = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    return {
        "hash": hash_hex,
        "element_count": len(elements),
    }


def do_detection_health(window_title: Optional[str] = None) -> dict:
    if sys.platform == "darwin":
        return {"backends": {"ax": {"available": True}}, "framework": "darwin"}
    return _orch().detection_health(window_title)


def register(server) -> int:
    """Register UI automation and inspector tools."""
    import base64 as _b64
    from mcp.server.fastmcp import Image as McpImage
    from tools.safety import with_timeout, ActionTimeoutError

    @server.tool()
    def find_element(
        name: str = "",
        role: str = "",
        window_title: str = "",
        index: int = 0,
        automation_id: str = "",
        class_name: str = "",
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> str:
        """Find a UI element by name, role, automation_id, or class_name.

        Parameters:
            name: Text label (partial, case-insensitive).
            role: Control type -- Button, Edit, MenuItem, etc.
            window_title: Partial title of target window (default: foreground).
            index: Which match to return if multiple (0 = first).
            automation_id: WPF/UWP AutomationId (exact match).
            class_name: Win32 class name (partial match).
            tree_mode: UIA tree view -- control, raw, or content.
            include_offscreen: Include off-screen elements.
        """
        try:
            result = with_timeout(
                lambda: do_find_element(
                    name=name or None,
                    role=role or None,
                    window_title=window_title or None,
                    index=index,
                    automation_id=automation_id or None,
                    class_name=class_name or None,
                    tree_mode=tree_mode or "control",
                    include_offscreen=include_offscreen,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 10s searching for element name='{name}', role='{role}'."
        if not result["found"]:
            return f"No element found matching name='{name}', role='{role}', automation_id='{automation_id}'. Error: {result.get('error', 'none')}"

        backend = result.get("backend_used", "uia")
        lines = [f"Found {len(result['elements'])} matching element(s) via {backend}:"]
        for i, elem in enumerate(result["elements"]):
            aid = f" id={elem['automation_id']}" if elem.get("automation_id") else ""
            lines.append(
                f"[{i}] {elem['role']} \"{elem['name']}\"{aid} "
                f"({elem['x']},{elem['y']}) {elem['width']}x{elem['height']}"
            )
        return "\n".join(lines)

    @server.tool()
    def click_element(
        name: str = "",
        role: str = "",
        window_title: str = "",
        index: int = 0,
        automation_id: str = "",
    ) -> list:
        """Find a UI element and click its center (or clickable point)."""
        try:
            result = with_timeout(
                lambda: do_click_element(
                    name=name or None,
                    role=role or None,
                    window_title=window_title or None,
                    index=index,
                    automation_id=automation_id or None,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 10s trying to click element name='{name}'."
        if not result["success"]:
            error = result["error"]
            if "nearest" in result:
                n = result["nearest"]
                error += (
                    f"\nNearest candidate: {n['element']['role']} \"{n['element']['name']}\" "
                    f"(confidence={n['confidence']})"
                )
            return f"Failed: {error}"

        from tools.screenshot import capture_screenshot
        shot = capture_screenshot()
        elem = result["element"]
        msg = (
            f"Clicked {elem['role']} \"{elem['name']}\" at "
            f"({result['clicked_at']['x']}, {result['clicked_at']['y']}) "
            f"via {result.get('backend_used', 'uia')}. Screenshot: {shot['width']}x{shot['height']}"
        )
        if result.get("fallback"):
            msg += f"\nFALLBACK: {result['note']}"
        if result.get("navigation_warning"):
            msg += f"\n⚠️ {result['navigation_warning']}"
        return [
            McpImage(data=_b64.b64decode(shot["image"]), format="png"),
            msg,
        ]

    @server.tool()
    def list_elements(
        window_title: str = "",
        max_depth: int = 5,
        role: str = "",
        tree_mode: str = "control",
        include_offscreen: bool = False,
    ) -> str:
        """List accessible UI elements in a window."""
        try:
            result = with_timeout(
                lambda: do_list_elements(
                    window_title=window_title or None,
                    max_depth=max_depth,
                    role=role or None,
                    tree_mode=tree_mode or "control",
                    include_offscreen=include_offscreen,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out after 10s listing UI elements."
        if not result["elements"]:
            return f"No elements found. {result.get('error', '')}"

        backend = result.get("backend_used", "uia")
        header = f"Found {result['count']} elements via {backend}"
        if role:
            header += f" with role '{role}'"
        header += ":"
        lines = [header]
        for i, elem in enumerate(result["elements"]):
            if not elem.get("name") and elem.get("role") in ("Pane", "Group", "Custom"):
                if not elem.get("automation_id") and not elem.get("class_name"):
                    continue
            name_str = f"\"{elem['name']}\"" if elem.get("name") else "(unnamed)"
            aid = f" id={elem['automation_id']}" if elem.get("automation_id") else ""
            lines.append(
                f"[{i}] {elem['role']} {name_str}{aid} "
                f"({elem['x']},{elem['y']}) {elem['width']}x{elem['height']}"
            )
            if i >= 100:
                lines.append(f"... and {result['count'] - 100} more (use role filter to narrow)")
                break
        return "\n".join(lines)

    @server.tool()
    def get_focused_element() -> str:
        """Get the currently focused UI element."""
        try:
            result = with_timeout(do_get_focused_element, timeout=5.0)
        except ActionTimeoutError:
            return "Timed out after 5s getting focused element."
        if not result["found"]:
            return f"Focus info unavailable. {result.get('error', '')}"
        e = result["element"]
        value_str = f" value=\"{e['value']}\"" if e.get("value") else ""
        return (
            f"Focused: {e['role']} \"{e['name']}\"{value_str} "
            f"at ({e['x']},{e['y']}) {e['width']}x{e['height']}"
        )

    @server.tool()
    def smart_find(
        name: str,
        role: str = "",
        window_title: str = "",
        index: int = 0,
        repo_path: str = "",
        agentic: bool = False,
        highlight: bool = False,
    ) -> str:
        """Find element via layered cascade: repo -> native -> OCR dual -> visual -> agentic."""
        try:
            result = with_timeout(
                lambda: do_smart_find(
                    name=name,
                    role=role or None,
                    window_title=window_title or None,
                    index=index,
                    repo_path=repo_path or None,
                    agentic=agentic,
                    highlight=highlight,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 20s searching for '{name}'."
        if not result["found"]:
            if result.get("agentic_context"):
                ctx = result["agentic_context"]
                lines = [f"Not found via layers. Agentic context for '{name}':",
                           f"Tree sample: {ctx.get('element_count', 0)} elements",
                           ctx.get("visual_regions", "")]
                for act in ctx.get("suggested_actions", [])[:5]:
                    lines.append(f"  → {act}")
                return "\n".join(lines)
            return f"Not found: {result.get('error', 'unknown')}"

        method = result.get("method") or result.get("layer", "")
        lines = [f"Found {len(result['elements'])} match(es) via {method}:"]
        if result.get("repo_updated"):
            lines.append("(object repository updated)")
        for i, elem in enumerate(result["elements"]):
            lines.append(
                f"[{i}] {elem['role']} \"{elem['name']}\" "
                f"({elem['x']},{elem['y']}) {elem['width']}x{elem['height']}"
            )
        return "\n".join(lines)

    @server.tool()
    def ui_fingerprint(window_title: str = "") -> str:
        """Quick hash of the current UI layout for change detection."""
        try:
            result = with_timeout(
                lambda: do_ui_fingerprint(window_title=window_title or None),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return "Timed out computing UI fingerprint."
        return f"UI fingerprint: {result['hash']} ({result['element_count']} elements)"

    @server.tool()
    def element_at_point(x: int, y: int) -> str:
        """Get the UI element at screen coordinates (like Automation Spy pick)."""
        try:
            result = with_timeout(lambda: do_element_at_point(x, y), timeout=5.0)
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"No element at ({x}, {y}). {result.get('error', '')}"
        e = result["element"]
        return (
            f"{e['role']} \"{e['name']}\" via {result.get('backend_used', 'uia')} "
            f"at ({e['x']},{e['y']}) {e['width']}x{e['height']}"
            + (f" automation_id={e['automation_id']}" if e.get("automation_id") else "")
        )

    @server.tool()
    def get_element_properties(
        name: str = "",
        automation_id: str = "",
        x: int = -1,
        y: int = -1,
        window_title: str = "",
    ) -> str:
        """Get full UIA properties for an element (Automation Spy style inspector)."""
        try:
            result = with_timeout(
                lambda: do_get_element_properties(
                    name=name or None,
                    automation_id=automation_id or None,
                    x=x if x >= 0 else None,
                    y=y if y >= 0 else None,
                    window_title=window_title or None,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"Not found. {result.get('error', '')}"
        props = result["properties"]
        lines = [f"Properties via {result.get('backend_used', 'uia')}:"]
        for k, v in sorted(props.items()):
            if k != "raw_properties" and v not in ("", None, [], {}):
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    @server.tool()
    def invoke_element(
        name: str = "",
        automation_id: str = "",
        window_title: str = "",
    ) -> str:
        """Invoke a button/menu via UIA InvokePattern (no coordinate click)."""
        try:
            result = with_timeout(
                lambda: do_invoke_element(
                    name=name or None,
                    automation_id=automation_id or None,
                    window_title=window_title or None,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if result.get("success"):
            return f"Invoked via {result.get('method', 'InvokePattern')}"
        return f"Failed: {result.get('error', 'unknown')}"

    @server.tool()
    def set_element_value(
        value: str,
        name: str = "",
        automation_id: str = "",
        window_title: str = "",
    ) -> str:
        """Set text field value via UIA ValuePattern."""
        try:
            result = with_timeout(
                lambda: do_set_element_value(
                    value=value,
                    name=name or None,
                    automation_id=automation_id or None,
                    window_title=window_title or None,
                ),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if result.get("success"):
            return f"Value set via {result.get('method', 'ValuePattern')}"
        return f"Failed: {result.get('error', 'unknown')}"

    @server.tool()
    def detection_health(window_title: str = "") -> str:
        """Report which detection backends are available and element counts."""
        try:
            result = with_timeout(
                lambda: do_detection_health(window_title or None),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        lines = [f"Framework: {result.get('framework', 'unknown')}"]
        lines.append(f"Recommended order: {', '.join(result.get('recommended_order', []))}")
        for name, info in result.get("backends", {}).items():
            status = "OK" if info.get("available") else "unavailable"
            count = info.get("element_count", "?")
            lines.append(f"  {name}: {status} ({count} elements)")
        return "\n".join(lines)

    @server.tool()
    def check_java_bridge() -> str:
        """Check Java Access Bridge prerequisites for Swing/AWT automation."""
        try:
            from detection.backends.jab_backend import check_java_bridge
            result = check_java_bridge()
        except ImportError:
            return "pyjab not installed. pip install pyjab for Java support."
        lines = [
            f"JAB available: {result.get('available', False)}",
            f"JAVA_HOME: {result.get('java_home') or '(not set)'}",
            f"pyjab installed: {result.get('pyjab_installed', False)}",
        ]
        for hint in result.get("hints", []):
            lines.append(f"  → {hint}")
        return "\n".join(lines)

    @server.tool()
    def detect_visual_regions(window_title: str = "") -> str:
        """Detect clickable UI regions via OpenCV + OCR (for opaque apps)."""
        from tools.screenshot import capture_screenshot
        from tools.visual_detect import detect_ui_regions, format_regions_text
        from tools.image_utils import load_image_from_screenshot
        shot = capture_screenshot(window_title=window_title or None)
        img = load_image_from_screenshot(shot)
        regions = detect_ui_regions(img, scale=1.0)
        return format_regions_text(regions)

    @server.tool()
    def repo_find(repo_path: str, window_title: str = "", highlight: bool = False) -> str:
        """Resolve a logical object from the UFT-style repository (e.g. frmMain/btnSave)."""
        try:
            result = with_timeout(
                lambda: do_repo_find(repo_path, window_title or None, highlight=highlight),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"Not found: {result.get('error', '')}"
        e = result["elements"][0]
        return (
            f"Resolved {repo_path} via {result.get('method', '')}: "
            f"{e['role']} \"{e['name']}\" at ({e['x']},{e['y']})"
        )

    @server.tool()
    def repo_list(window_title: str = "") -> str:
        """List objects stored in the repository for the active application."""
        result = do_repo_list(window_title or None)
        objs = result.get("objects", [])
        if not objs:
            return "Repository empty for this application."
        lines = [f"Repository ({result['app_id']}) — {len(objs)} object(s):"]
        for o in objs:
            lines.append(f"  {o['repo_path']} [{o.get('class', 'control')}]")
        return "\n".join(lines)

    @server.tool()
    def highlight_element(
        name: str = "",
        automation_id: str = "",
        repo_path: str = "",
        x: int = -1,
        y: int = -1,
        window_title: str = "",
        duration_ms: int = 3000,
    ) -> str:
        """Highlight an element on screen with a red border (Automation Spy style)."""
        from tools.highlight import highlight_element_dict, highlight_rect
        elem = None
        if repo_path:
            r = do_repo_find(repo_path, window_title or None)
            if r.get("found"):
                elem = r["elements"][0]
        elif name or automation_id:
            r = do_find_element(name=name or None, automation_id=automation_id or None,
                                window_title=window_title or None)
            if r.get("found"):
                elem = r["elements"][0]
        if elem:
            result = highlight_element_dict(elem, duration_ms=duration_ms)
            return f"Highlighted {elem.get('name', repo_path)}: {result}"
        if x >= 0 and y >= 0:
            result = highlight_rect(x, y, 40, 24, duration_ms=duration_ms)
            return f"Highlighted point ({x},{y}): {result}"
        return "Provide repo_path, name/automation_id, or x/y."

    @server.tool()
    def clear_highlight() -> str:
        """Remove on-screen highlight overlays."""
        from tools.highlight import clear_highlight
        return str(clear_highlight())

    @server.tool()
    def spy_inspect(
        name: str = "",
        automation_id: str = "",
        x: int = -1,
        y: int = -1,
        window_title: str = "",
    ) -> str:
        """Spy-grade full UIA property inspection (40+ fields)."""
        from tools.spy_bridge import spy_inspect_at, spy_inspect_element, spy_available
        if not spy_available():
            return "spy sidecar not built. Run mcp-servers/handson-spy-sidecar/build.cmd"
        if x >= 0 and y >= 0:
            result = spy_inspect_at(x, y)
        else:
            result = spy_inspect_element(name=name or None, automation_id=automation_id or None,
                                         window_title=window_title or None)
        if not result.get("found") and "properties" not in result:
            return f"Not found: {result.get('error', '')}"
        props = result.get("properties", result)
        lines = ["Spy inspection:"]
        for k, v in sorted(props.items()):
            if v not in ("", None, [], {}):
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    @server.tool()
    def spy_tree(window_title: str = "", mode: str = "control", max_depth: int = 5) -> str:
        """Walk UIA tree with Spy-grade detail."""
        from tools.spy_bridge import spy_tree, spy_available
        if not spy_available():
            return "spy sidecar not built."
        result = spy_tree(window_title, mode, max_depth)
        elements = result.get("elements", [])
        lines = [f"Spy tree: {result.get('count', len(elements))} elements"]
        for i, e in enumerate(elements[:50]):
            lines.append(f"  [{i}] {e.get('role')} \"{e.get('name')}\" id={e.get('automation_id', '')}")
        if len(elements) > 50:
            lines.append(f"  ... and {len(elements) - 50} more")
        return "\n".join(lines)

    @server.tool()
    def build_detection_context(name: str = "", window_title: str = "") -> str:
        """Rich agentic context: screenshot, tree, OCR dual, visual regions, suggestions."""
        try:
            ctx = with_timeout(
                lambda: do_build_detection_context(name, window_title or None),
                timeout=25.0,
            )
        except ActionTimeoutError:
            return "Timed out building detection context."
        if not ctx:
            return "No context available."
        lines = [
            f"Detection context for '{name or '(all)'}':",
            f"Screenshot: {ctx.get('screenshot_path', '')}",
            f"Accessibility tree: {ctx.get('element_count', 0)} elements (sample below)",
        ]
        for e in ctx.get("tree_sample", [])[:10]:
            lines.append(f"  {e.get('role')} \"{e.get('name')}\"")
        lines.append(ctx.get("visual_regions", ""))
        lines.append("Suggested actions:")
        for act in ctx.get("suggested_actions", [])[:8]:
            lines.append(f"  {act}")
        return "\n".join(lines)

    return 20
