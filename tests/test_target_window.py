"""Tests for the target window auto-focus feature.

Validates session state management and that ensure_focus() is called
by input tool backends.
"""

import os
import sys
from unittest import mock

import pytest

# Make the handson-server package importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


# ---------------------------------------------------------------------------
# Test: set_target / get_target
# ---------------------------------------------------------------------------

class TestTargetState:
    def setup_method(self):
        """Reset state between tests."""
        from tools import target_window
        target_window._target_window = None

    def test_set_and_get_target(self):
        from tools.target_window import set_target, get_target
        set_target("My Browser")
        assert get_target() == "My Browser"

    def test_clear_with_none(self):
        from tools.target_window import set_target, get_target
        set_target("Something")
        set_target(None)
        assert get_target() is None

    def test_clear_with_empty_string(self):
        from tools.target_window import set_target, get_target
        set_target("Something")
        set_target("")
        assert get_target() is None

    def test_clear_with_whitespace(self):
        from tools.target_window import set_target, get_target
        set_target("Something")
        set_target("   ")
        assert get_target() is None

    def test_default_is_none(self):
        from tools.target_window import get_target
        assert get_target() is None


# ---------------------------------------------------------------------------
# Test: ensure_focus
# ---------------------------------------------------------------------------

class TestEnsureFocus:
    def setup_method(self):
        from tools import target_window
        target_window._target_window = None

    @mock.patch("tools.windows.do_focus_window")
    def test_calls_do_focus_window_when_target_set(self, mock_focus):
        from tools.target_window import set_target, ensure_focus
        mock_focus.return_value = {"success": True, "window": "Browser", "action": "focus"}
        set_target("Browser")
        ensure_focus()
        mock_focus.assert_called_once_with("Browser", action="focus")

    @mock.patch("tools.windows.do_focus_window")
    def test_noop_when_no_target(self, mock_focus):
        from tools.target_window import ensure_focus
        ensure_focus()
        mock_focus.assert_not_called()


# ---------------------------------------------------------------------------
# Test: input tools call ensure_focus
# ---------------------------------------------------------------------------

class TestInputToolsCallEnsureFocus:
    """Verify that each do_* function calls ensure_focus() before acting."""

    @mock.patch("tools.screenshot.capture_screenshot")
    @mock.patch("tools.windows.get_foreground_title", return_value="App")
    @mock.patch("tools.target_window.ensure_focus")
    @mock.patch("tools.input_tools.pyautogui")
    def test_do_click_calls_ensure_focus(self, mock_pag, mock_ef, mock_title, mock_cap):
        # Need valid base64 image for compare_screenshots
        import base64, io, numpy as np
        from PIL import Image
        arr = np.full((100, 100, 3), 128, dtype=np.uint8)
        buf = io.BytesIO(); Image.fromarray(arr).save(buf, format="JPEG", quality=80)
        mock_cap.return_value = {"image": base64.b64encode(buf.getvalue()).decode(), "width": 100, "height": 100, "path": "/f.png", "dpi_scale": 1.0}
        from tools.input_tools import do_click
        do_click(100, 200)
        # Called twice: before click and after sleep (to re-focus before title check)
        assert mock_ef.call_count == 2

    @mock.patch("tools.target_window.ensure_focus")
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.input_tools.get_foreground_type", return_value={"type": "gui", "pid": 0, "hwnd": 0})
    def test_do_type_text_calls_ensure_focus(self, mock_fg, mock_pag, mock_ef):
        from tools.input_tools import do_type_text
        do_type_text("hello")
        mock_ef.assert_called_once()

    @mock.patch("tools.target_window.ensure_focus")
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.input_tools.get_foreground_type", return_value={"type": "gui", "pid": 0, "hwnd": 0})
    def test_do_send_keys_calls_ensure_focus(self, mock_fg, mock_pag, mock_ef):
        from tools.input_tools import do_send_keys
        do_send_keys("enter")
        mock_ef.assert_called_once()

    @mock.patch("tools.screenshot.capture_screenshot")
    @mock.patch("tools.target_window.ensure_focus")
    @mock.patch("tools.input_tools.pyautogui")
    def test_do_scroll_calls_ensure_focus(self, mock_pag, mock_ef, mock_cap):
        import base64, io, numpy as np
        from PIL import Image
        arr = np.full((100, 100, 3), 128, dtype=np.uint8)
        buf = io.BytesIO(); Image.fromarray(arr).save(buf, format="JPEG", quality=80)
        mock_cap.return_value = {"image": base64.b64encode(buf.getvalue()).decode(), "width": 100, "height": 100, "path": "/f.png", "dpi_scale": 1.0}
        from tools.input_tools import do_scroll
        do_scroll(500, 400, "up")
        mock_ef.assert_called_once()

    @mock.patch("tools.target_window.ensure_focus")
    @mock.patch("tools.input_tools.pyautogui")
    def test_do_drag_calls_ensure_focus(self, mock_pag, mock_ef):
        from tools.input_tools import do_drag
        do_drag(0, 0, 100, 100)
        mock_ef.assert_called_once()

    @mock.patch("tools.target_window.ensure_focus")
    @mock.patch("tools.input_tools.pyautogui")
    def test_do_hover_calls_ensure_focus(self, mock_pag, mock_ef):
        from tools.input_tools import do_hover
        do_hover(50, 60)
        mock_ef.assert_called_once()


# ---------------------------------------------------------------------------
# Test: register (tool count)
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_returns_two(self):
        from tools.target_window import register

        mock_server = mock.MagicMock()
        mock_server.tool.return_value = lambda fn: fn
        count = register(mock_server)
        assert count == 2
        assert mock_server.tool.call_count == 2

