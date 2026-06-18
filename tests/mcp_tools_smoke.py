"""Smoke test all HandsOn MCP tools via direct Python calls."""
from __future__ import annotations

import json
import os
import site
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_DIR = os.path.join(ROOT, "mcp-servers", "handson-server")
sys.path.insert(0, SERVER_DIR)

_VENV_SITE = os.path.join(os.path.expanduser("~"), ".handson", ".venv", "Lib", "site-packages")
if os.path.exists(_VENV_SITE):
    site.addsitedir(_VENV_SITE)
    sys.path.insert(0, _VENV_SITE)

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = ""):
    RESULTS.append({"tool": name, "ok": ok, "detail": detail[:800]})
    print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail[:150]}")


def safe(name: str, fn, ok_if=None):
    try:
        out = fn()
        if ok_if is not None:
            record(name, bool(ok_if(out)), str(out)[:200])
        elif isinstance(out, dict) and out.get("success") is False:
            record(name, False, str(out))
        elif isinstance(out, dict) and out.get("error") and name.startswith(("spy_", "clear_")):
            record(name, False, str(out))
        else:
            record(name, True, str(out)[:200])
    except Exception as e:
        record(name, False, f"{type(e).__name__}: {e}")


def main() -> int:
    print("=== HandsOn Full Tools Smoke Test ===\n")

    import tempfile
    import tools.screenshot as screenshot_mod
    from screenshot_manager import ScreenshotManager
    import version_check
    from detection.backends.jab_backend import check_java_bridge
    from detection.discovery.executor import apply_probe
    from detection.discovery.observer import observe_ui
    from detection.discovery.planner import plan_probes
    from detection.discovery.runner import discover_target
    from tools.batch import do_batch_actions
    from tools.framework_detect import do_detect_framework
    from tools.highlight import clear_highlight, highlight_element_dict
    from tools.image_utils import load_image_from_screenshot
    from tools.input_tools import (
        do_click,
        do_drag,
        do_get_mouse_position,
        do_hover,
        do_scroll,
        do_send_keys,
        do_type_text,
    )
    from tools.manage import do_clipboard_read, do_clipboard_write
    from tools.ocr import do_click_text, do_find_text
    from tools.screenshot import capture_screenshot, get_screen_size, wait_for_change
    from tools.spy_bridge import spy_available, spy_inspect_element, spy_tree
    from tools.spy_walk import spy_walk_visible
    from tools.target_window import get_target, set_target
    from tools.template_match import find_by_template
    from tools.uac import do_configure_uac
    from tools.ui_automation import (
        do_build_detection_context,
        do_click_element,
        do_detection_health,
        do_element_at_point,
        do_find_element,
        do_get_element_properties,
        do_get_focused_element,
        do_invoke_element,
        do_list_elements,
        do_repo_find,
        do_repo_list,
        do_set_element_value,
        do_smart_find,
        do_ui_fingerprint,
    )
    from tools.visual_detect import detect_ui_regions
    from tools.visual_diff import compute_visual_diff
    from tools.watcher import do_get_notifications, do_start_watcher, do_stop_watcher
    from tools.windows import do_focus_window, do_launch_app, do_list_windows

    screenshot_mod.screenshot_manager = ScreenshotManager(
        os.path.join(tempfile.gettempdir(), "handson_screenshots")
    )

    # System / utility
    safe("check_version", lambda: version_check.check_version(force=False))
    safe("detection_health", lambda: do_detection_health())
    safe("check_java_bridge", lambda: check_java_bridge())
    safe("get_screen_size", lambda: get_screen_size())
    safe("get_mouse_position", lambda: do_get_mouse_position())
    safe("get_target_window", lambda: get_target() or "No target")
    safe("list_windows", lambda: len(do_list_windows()))
    safe("configure_uac", lambda: do_configure_uac("status"))
    safe("clipboard (read)", lambda: do_clipboard_read()[:60])
    safe("manage_screenshots", lambda: len(screenshot_mod.screenshot_manager.list_screenshots()))
    safe("detect_framework", lambda: do_detect_framework("Cursor"))
    safe("repo_list", lambda: do_repo_list())

    print("\n--- Notepad session ---")
    launch = do_launch_app("notepad.exe")
    record("launch_app", launch.get("success", False), str(launch))
    time.sleep(1.2)
    do_focus_window("Bloc de notas", "focus")
    set_target("Bloc de notas")
    time.sleep(0.5)

    safe("set_target_window", lambda: get_target())
    safe("focus_window", lambda: do_focus_window("Bloc de notas", "focus"))
    safe("list_elements", lambda: do_list_elements(window_title="Bloc de notas"))
    safe("find_element", lambda: do_find_element(name="Editor de texto", window_title="Bloc de notas"))
    safe("get_focused_element", lambda: do_get_focused_element())
    safe("ui_fingerprint", lambda: do_ui_fingerprint("Bloc de notas"))
    safe("smart_find", lambda: do_smart_find(name="Editor de texto", window_title="Bloc de notas"))
    safe("detect_framework (Notepad)", lambda: do_detect_framework("Bloc de notas"))
    safe("find_text", lambda: do_find_text("Archivo", window_title="Bloc de notas"))
    safe("click_text", lambda: do_click_text("Archivo", window_title="Bloc de notas"))
    safe("build_detection_context", lambda: do_build_detection_context(window_title="Bloc de notas"))
    safe("repo_find", lambda: do_repo_find("frmMain/btnSave", "Bloc de notas"))

    if spy_available():
        safe("spy_tree", lambda: spy_tree(window_title="Bloc de notas", max_depth=2))
        safe("spy_inspect", lambda: spy_inspect_element(name="Editor de texto", window_title="Bloc de notas"))
        safe("spy_walk_visible_tool", lambda: spy_walk_visible(window_title="Bloc de notas", batch_size=3))

    elems = do_list_elements(window_title="Bloc de notas")
    elements = elems.get("elements") or []
    if elements:
        el = next((e for e in elements if e.get("role") == "Edit"), elements[0])
        cx = int(el.get("center_x") or el.get("x", 500))
        cy = int(el.get("center_y") or el.get("y", 400))
        safe("element_at_point", lambda: do_element_at_point(cx, cy))
        safe("get_element_properties", lambda: do_get_element_properties(
            name=el.get("name", ""), x=cx, y=cy, window_title="Bloc de notas"
        ))
        safe("highlight_element", lambda: highlight_element_dict(el))
        safe("click_element", lambda: do_click_element(name="Editor de texto", window_title="Bloc de notas"))
        safe("set_element_value", lambda: do_set_element_value(
            "HandsOn test", name="Editor de texto", window_title="Bloc de notas"
        ))
        safe("invoke_element", lambda: do_invoke_element(name="Archivo", window_title="Bloc de notas"))

    shot = capture_screenshot()
    safe("screenshot", lambda: f"{shot['width']}x{shot['height']}")
    safe("detect_visual_regions", lambda: len(detect_ui_regions(load_image_from_screenshot(shot))))
    safe("observe_ui_tool", lambda: observe_ui("Bloc de notas"))
    obs = observe_ui("Bloc de notas")
    safe("plan_probes_tool", lambda: plan_probes(goal="open Archivo menu", observation=obs))
    safe("apply_probe_tool", lambda: apply_probe("press_key", target="alt", window_title="Bloc de notas"))
    safe("discover_target_tool", lambda: discover_target("Archivo menu", window_title="Bloc de notas", max_steps=1))
    safe("find_by_template_tool", lambda: find_by_template("nonexistent.png"))

    baseline = capture_screenshot()
    diff = compute_visual_diff(baseline["image"], baseline["image"])
    safe("screenshot_baseline", lambda: f"{baseline['width']}x{baseline['height']}")
    safe("screenshot_diff", lambda: diff["is_identical"])

    safe("click", lambda: do_click(500, 400))
    safe("type_text", lambda: do_type_text(" smoke"))
    safe("send_keys", lambda: do_send_keys("home"))
    safe("scroll", lambda: do_scroll(500, 400, "down", 1))
    safe("hover", lambda: do_hover(400, 350))
    safe("drag", lambda: do_drag(400, 350, 450, 380))
    safe("batch_actions", lambda: do_batch_actions([{"action": "wait", "ms": 100}]))
    safe("wait_for_change", lambda: wait_for_change(timeout=0.5))
    safe("clear_highlight", lambda: clear_highlight())

    w = do_start_watcher(poll_interval=1.0, capture_snippets=False)
    record("start_watcher", w.get("started", True), str(w))
    time.sleep(1.0)
    safe("get_notifications", lambda: do_get_notifications(clear=False))
    safe("stop_watcher", lambda: do_stop_watcher())

    token = "__handson_smoke__"
    do_clipboard_write(token)
    safe("clipboard (write)", lambda: do_clipboard_read(), ok_if=lambda v: v == token)

    do_send_keys("alt+f4")
    time.sleep(0.4)
    do_send_keys("n")
    set_target("")
    safe("set_target_window (clear)", lambda: get_target() or "cleared")

    ok = sum(1 for r in RESULTS if r["ok"])
    fail = len(RESULTS) - ok
    print(f"\n=== SUMMARY: {ok} OK, {fail} FAIL / {len(RESULTS)} ===")
    for r in RESULTS:
        if not r["ok"]:
            print(f"  FAIL: {r['tool']} -> {r['detail'][:200]}")

    out = os.path.join(ROOT, "smoke_test_results.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
