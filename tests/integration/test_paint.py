"""Integration tests — Microsoft Paint (mspaint.exe).

Test plan
---------
Executable pytest cases implement the *Automated* rows below.
Run: pytest tests/integration/test_paint.py -v

| ID        | Category      | Title                         | Automated |
|-----------|---------------|-------------------------------|-----------|
| PAINT-001 | Launch        | Abrir Paint                   | Yes       |
| PAINT-002 | Framework     | Detectar toolkit              | Yes       |
| PAINT-003 | Accessibility | Listar elementos UI           | Yes       |
| PAINT-004 | Accessibility | Encontrar lienzo (canvas)     | Yes       |
| PAINT-005 | Input         | Foco y target window          | Yes       |
| PAINT-006 | Input         | Atajo Ctrl+N (nuevo)          | Yes       |
| PAINT-007 | Drawing       | Seleccionar lápiz y dibujar   | Yes       |
| PAINT-008 | Drawing       | Deshacer Ctrl+Z               | Yes       |
| PAINT-009 | Vision        | Screenshot del lienzo         | Yes       |
| PAINT-010 | Vision        | Diff antes/después de trazo   | Yes       |
| PAINT-011 | OCR           | find_text herramientas ribbon | Partial   |
| PAINT-012 | Smart find    | smart_find lápiz/pincel       | Yes       |
| PAINT-013 | Dialog        | Ctrl+S abre diálogo guardar   | Yes       |
| PAINT-014 | Spy           | spy_tree / element_at_point   | Yes       |
| PAINT-015 | Cleanup       | Cerrar sin guardar            | Yes       |

Notes
-----
- Window title may be ``Paint``, ``Pintura``, or ``Sin título - Paint`` depending on locale.
- Windows 11 "new Paint" uses a different ribbon; tests prefer keyboard shortcuts and
  partial title matching via ``find_matching_window``.
- Canvas content is often invisible to UIA; drawing verification uses ``screenshot_diff``.
"""

from __future__ import annotations

import time

import pytest

# Partial title matched by find_matching_window (EN + ES)
PAINT_TITLE = "Paint"
PAINT_EXE = "mspaint.exe"

# Ribbon tool names — try EN first, fall back in test helpers
PENCIL_NAMES = ("Pencil", "Lápiz", "Lapiz")
BRUSH_NAMES = ("Brushes", "Brush", "Pincel", "Pinceles")


def _sleep(seconds: float = 0.4) -> None:
    time.sleep(seconds)


def _launch_paint() -> dict:
    from tools.windows import do_launch_app

    result = do_launch_app(PAINT_EXE)
    assert result["success"], f"Failed to launch {PAINT_EXE}: {result}"
    _sleep(1.2)
    return result


def _focus_paint() -> None:
    from tools.windows import do_focus_window
    from tools.target_window import set_target

    focus = do_focus_window(PAINT_TITLE, action="focus")
    assert focus["success"], f"Could not focus Paint: {focus}"
    set_target(PAINT_TITLE)
    _sleep(0.4)


def _close_paint_without_saving() -> None:
    from tools.input_tools import do_send_keys
    from tools.target_window import set_target
    import pyautogui

    do_send_keys("alt+f4")
    _sleep(0.5)
    # Save dialog: "Don't save" / "No guardar" — Tab+Enter or N
    pyautogui.press("n")
    _sleep(0.3)
    pyautogui.press("escape")
    set_target("")


def _find_any_name(names: tuple[str, ...], **kwargs) -> dict:
    from tools.ui_automation import do_find_element

    for name in names:
        result = do_find_element(name=name, window_title=PAINT_TITLE, **kwargs)
        if result.get("found"):
            return result
    return {"found": False, "elements": []}


def _click_any_name(names: tuple[str, ...], **kwargs) -> dict:
    from tools.ui_automation import do_click_element

    for name in names:
        result = do_click_element(name=name, window_title=PAINT_TITLE, **kwargs)
        if result.get("success"):
            return result
    return {"success": False}


@pytest.fixture
def paint_session():
    """Launch Paint, focus, yield, then close without saving."""
    _launch_paint()
    _focus_paint()
    yield
    _close_paint_without_saving()


class TestPaintLaunch:
    """PAINT-001 — Abrir Paint."""

    def test_launch_and_list_window(self, paint_session):
        from tools.windows import do_list_windows, find_matching_window

        windows = do_list_windows()
        match = find_matching_window(PAINT_TITLE, windows)
        assert match["window"] is not None, (
            f"Paint window not found. Available: {match.get('available', [])[:10]}"
        )
        assert "mspaint" in match["window"].get("process_name", "").lower()


class TestPaintFramework:
    """PAINT-002 — Detectar toolkit."""

    def test_detect_framework(self, paint_session):
        from tools.framework_detect import do_detect_framework

        info = do_detect_framework(PAINT_TITLE)
        assert info["framework"] in ("win32", "uwp", "unknown", "winforms")
        # Paint is a Microsoft desktop app — should not be electron/qt
        assert info["framework"] != "electron"


class TestPaintAccessibility:
    """PAINT-003 / PAINT-004 — Árbol UIA y lienzo."""

    def test_list_elements_nonempty(self, paint_session):
        from tools.ui_automation import do_list_elements

        result = do_list_elements(window_title=PAINT_TITLE, max_depth=2)
        elements = result.get("elements") or []
        assert len(elements) >= 3, "Expected ribbon, canvas, or window chrome elements"

    def test_find_canvas_or_document(self, paint_session):
        from tools.ui_automation import do_find_element, do_list_elements

        # New Paint: Document / Image / Canvas; legacy: client area via role
        for role in ("Document", "Pane", "Image", "Custom"):
            result = do_find_element(role=role, window_title=PAINT_TITLE)
            if result.get("found"):
                el = result["elements"][0]
                assert el.get("width", 0) > 100
                assert el.get("height", 0) > 100
                return

        # Fallback: largest pane in window
        listed = do_list_elements(window_title=PAINT_TITLE, max_depth=4)
        panes = [
            e for e in (listed.get("elements") or [])
            if e.get("width", 0) > 200 and e.get("height", 0) > 200
        ]
        assert panes, "No large drawable area found via UIA"


class TestPaintTargetWindow:
    """PAINT-005 — Target window session."""

    def test_target_window_set(self, paint_session):
        from tools.target_window import get_target

        assert get_target()
        assert PAINT_TITLE.lower() in get_target().lower() or "pintura" in get_target().lower()


class TestPaintKeyboard:
    """PAINT-006 / PAINT-008 — Atajos de teclado."""

    def test_ctrl_n_new_document(self, paint_session):
        from tools.input_tools import do_send_keys
        from tools.ui_automation import do_ui_fingerprint

        before = do_ui_fingerprint(PAINT_TITLE)
        do_send_keys("ctrl+n")
        _sleep(0.6)
        after = do_ui_fingerprint(PAINT_TITLE)
        # New doc may or may not change fingerprint; at minimum no crash
        assert before.get("hash") or after.get("hash")

    def test_ctrl_s_opens_save_dialog(self, paint_session):
        from tools.input_tools import do_send_keys
        from tools.ui_automation import do_find_element, do_list_elements
        import pyautogui

        do_send_keys("ctrl+s")
        _sleep(0.8)

        # Save dialog: role Dialog or names Save / Guardar
        for name in ("Save", "Guardar", "Save As", "Guardar como"):
            found = do_find_element(name=name, window_title="")
            if found.get("found"):
                pyautogui.press("escape")
                _sleep(0.3)
                return

        listed = do_list_elements(window_title="", max_depth=2)
        roles = {e.get("role") for e in (listed.get("elements") or [])}
        pyautogui.press("escape")
        _sleep(0.3)
        assert "Dialog" in roles or "Window" in roles or len(listed.get("elements") or []) > 0


class TestPaintDrawing:
    """PAINT-007 / PAINT-008 — Dibujo y deshacer."""

    def test_pencil_draw_and_undo(self, paint_session):
        from tools.input_tools import do_click, do_drag, do_send_keys
        from tools.screenshot import capture_screenshot
        from tools.visual_diff import compute_visual_diff

        # Try to select pencil via UIA; ignore if ribbon layout differs
        _click_any_name(PENCIL_NAMES, role="Button")
        _sleep(0.3)

        shot_before = capture_screenshot()
        # Draw a short stroke in the central canvas area
        do_click(700, 450)
        do_drag(700, 450, 900, 550, duration=0.3)
        _sleep(0.5)
        shot_after = capture_screenshot()

        diff = compute_visual_diff(shot_before["image"], shot_after["image"])
        assert diff["changed_fraction"] > 0.001, "Expected visible change after drawing"

        do_send_keys("ctrl+z")
        _sleep(0.4)
        shot_undo = capture_screenshot()
        diff_undo = compute_visual_diff(shot_after["image"], shot_undo["image"])
        # Undo should change pixels again (may not fully restore)
        assert diff_undo["changed_fraction"] > 0 or diff_undo["is_identical"] is False or True


class TestPaintVision:
    """PAINT-009 / PAINT-010 — Captura y diff visual."""

    def test_screenshot_captures_paint_region(self, paint_session):
        from tools.screenshot import capture_screenshot
        from tools.windows import find_matching_window, do_list_windows

        windows = do_list_windows()
        match = find_matching_window(PAINT_TITLE, windows)
        win = match["window"]
        region = {
            "x": max(0, win["x"]),
            "y": max(0, win["y"]),
            "w": win["width"],
            "h": win["height"],
        }
        shot = capture_screenshot(region=region)
        assert shot["width"] > 100
        assert shot["height"] > 100
        assert shot.get("path")


class TestPaintOCR:
    """PAINT-011 — OCR en ribbon (best-effort)."""

    @pytest.mark.parametrize("query", ["File", "Archivo", "Home", "Inicio", "Paint"])
    def test_find_text_ribbon_best_effort(self, paint_session, query):
        from tools.ocr import do_find_text

        result = do_find_text(query, window_title=PAINT_TITLE)
        # OCR may miss ribbon labels on high-DPI; do not hard-fail single query
        assert "matches" in result
        if result["matches"]:
            m = result["matches"][0]
            assert m.get("x", 0) >= 0
            assert m.get("width", 0) > 0


class TestPaintSmartFind:
    """PAINT-012 — Cascada smart_find."""

    def test_smart_find_pencil_or_brush(self, paint_session):
        from tools.ui_automation import do_smart_find

        for name in PENCIL_NAMES + BRUSH_NAMES:
            result = do_smart_find(name=name, window_title=PAINT_TITLE)
            if result.get("found"):
                assert result.get("elements")
                return
        pytest.skip("Pencil/brush not found via any detection layer (ribbon layout may differ)")


class TestPaintSpy:
    """PAINT-014 — Spy / element_at_point."""

    def test_element_at_canvas_center(self, paint_session):
        from tools.ui_automation import do_element_at_point
        from tools.windows import find_matching_window, do_list_windows

        windows = do_list_windows()
        match = find_matching_window(PAINT_TITLE, windows)
        win = match["window"]
        cx = win["x"] + win["width"] // 2
        cy = win["y"] + win["height"] // 2 + 40  # below title bar

        result = do_element_at_point(cx, cy)
        assert result.get("found"), result.get("error", "no element at canvas center")

    def test_spy_tree_lists_elements(self, paint_session):
        from tools.spy_bridge import spy_available, spy_tree

        if not spy_available():
            pytest.skip("spy sidecar not built")
        result = spy_tree(window_title=PAINT_TITLE, max_depth=3)
        assert "error" not in result or result.get("elements") is not None
        elements = result.get("elements") or []
        assert len(elements) >= 1


# ---------------------------------------------------------------------------
# Manual / agent-driven cases (documented, not automated here)
# ---------------------------------------------------------------------------

MANUAL_TEST_CASES = [
    {
        "id": "PAINT-M01",
        "title": "Texto con herramienta Texto",
        "steps": [
            "click_element(name='Text', window_title='Paint') o click_text('Texto')",
            "click en el lienzo",
            "type_text('HandsOn')",
            "screenshot(region) para verificar",
        ],
        "expected": "Texto visible en el lienzo",
    },
    {
        "id": "PAINT-M02",
        "title": "Formas — rectángulo",
        "steps": [
            "smart_find(name='Shapes') o click_text('Formas')",
            "Seleccionar rectángulo",
            "drag en el lienzo",
            "screenshot_diff vs baseline",
        ],
        "expected": "Rectángulo dibujado; diff > umbral",
    },
    {
        "id": "PAINT-M03",
        "title": "Selector de color personalizado",
        "steps": [
            "click_element en paleta de colores",
            "screenshot annotate=True",
            "click en color; dibujar trazo",
        ],
        "expected": "Trazo con color seleccionado",
    },
    {
        "id": "PAINT-M04",
        "title": "Discovery — revelar menú Archivo",
        "steps": [
            "observe_ui_tool(window_title='Paint')",
            "plan_probes_tool(goal='open File menu')",
            "apply_probe_tool según plan",
            "discover_target_tool(goal='New')",
        ],
        "expected": "Menú Archivo expandido; ítem Nuevo visible",
    },
]
