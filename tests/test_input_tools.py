"""Tests for the input tools (click, type_text, send_keys, scroll, drag, hover).

Validates helper/validation functions and core function behaviour with mocked
pyautogui (actual display interactions are not tested).
"""

import base64
import io
import os
import sys
from unittest import mock

import numpy as np
import pytest
from PIL import Image

# Make the handson-server package importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


def _make_fake_shot():
    """Build a fake capture_screenshot() result with valid base64 image."""
    arr = np.full((100, 100, 3), 128, dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"image": b64, "width": 100, "height": 100, "path": "/fake.png", "dpi_scale": 1.0}


_FAKE_SHOT = _make_fake_shot()


# ---------------------------------------------------------------------------
# Test: parse_hotkey
# ---------------------------------------------------------------------------

class TestKeyParsing:
    def test_parse_single_key(self):
        from tools.input_tools import parse_hotkey
        assert parse_hotkey("enter") == ["enter"]

    def test_parse_combo(self):
        from tools.input_tools import parse_hotkey
        result = parse_hotkey("ctrl+s")
        assert result == ["ctrl", "s"]

    def test_parse_complex_combo(self):
        from tools.input_tools import parse_hotkey
        result = parse_hotkey("ctrl+shift+p")
        assert result == ["ctrl", "shift", "p"]

    def test_parse_strips_whitespace(self):
        from tools.input_tools import parse_hotkey
        result = parse_hotkey("ctrl + alt + delete")
        assert result == ["ctrl", "alt", "delete"]

    def test_parse_lowercases(self):
        from tools.input_tools import parse_hotkey
        result = parse_hotkey("CTRL+SHIFT+S")
        assert result == ["ctrl", "shift", "s"]


# ---------------------------------------------------------------------------
# Test: validate_button
# ---------------------------------------------------------------------------

class TestButtonValidation:
    def test_valid_buttons(self):
        from tools.input_tools import validate_button
        assert validate_button("left") == "left"
        assert validate_button("right") == "right"
        assert validate_button("middle") == "middle"

    def test_case_insensitive(self):
        from tools.input_tools import validate_button
        assert validate_button("LEFT") == "left"
        assert validate_button("Right") == "right"
        assert validate_button("MIDDLE") == "middle"

    def test_invalid_button_raises(self):
        from tools.input_tools import validate_button
        with pytest.raises(ValueError, match="Invalid button"):
            validate_button("invalid")

    def test_empty_string_raises(self):
        from tools.input_tools import validate_button
        with pytest.raises(ValueError):
            validate_button("")


# ---------------------------------------------------------------------------
# Test: validate_direction
# ---------------------------------------------------------------------------

class TestDirectionValidation:
    def test_valid_directions(self):
        from tools.input_tools import validate_direction
        assert validate_direction("up") == "up"
        assert validate_direction("down") == "down"
        assert validate_direction("left") == "left"
        assert validate_direction("right") == "right"

    def test_case_insensitive(self):
        from tools.input_tools import validate_direction
        assert validate_direction("UP") == "up"
        assert validate_direction("Down") == "down"

    def test_invalid_direction_raises(self):
        from tools.input_tools import validate_direction
        with pytest.raises(ValueError, match="Invalid direction"):
            validate_direction("sideways")

    def test_empty_string_raises(self):
        from tools.input_tools import validate_direction
        with pytest.raises(ValueError):
            validate_direction("")


# ---------------------------------------------------------------------------
# Test: do_click (mocked pyautogui)
# ---------------------------------------------------------------------------

class TestDoClick:
    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.windows.get_foreground_title", return_value="App")
    @mock.patch("tools.input_tools.pyautogui")
    def test_basic_click(self, mock_pag, mock_title, mock_cap):
        from tools.input_tools import do_click
        result = do_click(100, 200)
        mock_pag.click.assert_called_once_with(x=100, y=200, button="left", clicks=1)
        assert result["action"] == "click"
        assert result["x"] == 100
        assert result["y"] == 200

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.windows.get_foreground_title", return_value="App")
    @mock.patch("tools.input_tools.pyautogui")
    def test_right_click(self, mock_pag, mock_title, mock_cap):
        from tools.input_tools import do_click
        result = do_click(50, 60, button="right")
        mock_pag.click.assert_called_once_with(x=50, y=60, button="right", clicks=1)
        assert result["button"] == "right"

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.windows.get_foreground_title", return_value="App")
    @mock.patch("tools.input_tools.pyautogui")
    def test_double_click(self, mock_pag, mock_title, mock_cap):
        from tools.input_tools import do_click
        result = do_click(10, 20, clicks=2)
        mock_pag.click.assert_called_once_with(x=10, y=20, button="left", clicks=2)
        assert result["clicks"] == 2

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.windows.get_foreground_title", return_value="App")
    @mock.patch("tools.input_tools.pyautogui")
    def test_invalid_button_raises(self, mock_pag, mock_title, mock_cap):
        from tools.input_tools import do_click
        with pytest.raises(ValueError):
            do_click(10, 20, button="bad")


class TestNavigationWarning:
    """Tests for post-click navigation detection."""

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.windows.get_foreground_title")
    def test_no_warning_when_title_unchanged(self, mock_title, mock_pag, mock_cap):
        mock_title.return_value = "Submit to r/ClaudeCode"
        from tools.input_tools import do_click
        result = do_click(100, 200)
        assert "navigation_warning" not in result

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.windows.get_foreground_title")
    def test_warning_when_title_changes(self, mock_title, mock_pag, mock_cap):
        mock_title.side_effect = [
            "Submit to r/ClaudeCode",  # pre-click
            "Reddit - News",           # post-click
        ]
        from tools.input_tools import do_click
        result = do_click(100, 200)
        assert "navigation_warning" in result
        assert "Submit to r/ClaudeCode" in result["navigation_warning"]
        assert "Reddit - News" in result["navigation_warning"]

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.windows.get_foreground_title")
    def test_no_warning_when_title_empty(self, mock_title, mock_pag, mock_cap):
        mock_title.return_value = ""
        from tools.input_tools import do_click
        result = do_click(100, 200)
        assert "navigation_warning" not in result

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_warning_propagates_through_click_text(self, mock_find, mock_click):
        mock_find.return_value = {
            "matches": [{"text": "News", "x": 100, "y": 200, "width": 50, "height": 20}],
            "total_words": 10,
        }
        mock_click.return_value = {
            "action": "click",
            "visual_change": True,
            "pixel_diff": 0.05,
            "navigation_warning": "Window title changed: 'Submit to r/ClaudeCode' → 'Reddit - Popular'",
        }
        from tools.ocr import do_click_text
        result = do_click_text("News")
        assert result["success"] is True
        assert "navigation_warning" in result

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.windows.get_foreground_title")
    def test_warning_propagates_through_click_element(self, mock_title, mock_pag, mock_cap):
        mock_title.side_effect = [
            "My App - Settings",
            "My App - Home",
        ]
        from tools.ui_automation import do_click_element
        with mock.patch("tools.ui_automation.do_find_element") as mock_find:
            mock_find.return_value = {
                "found": True,
                "elements": [{"name": "Home", "role": "Button", "x": 50, "y": 50, "width": 80, "height": 30}],
                "count": 1,
            }
            result = do_click_element(name="Home", role="Button")
            assert result["success"] is True
            assert "navigation_warning" in result

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    @mock.patch("tools.windows.get_foreground_title")
    @mock.patch("tools.target_window.ensure_focus")
    def test_no_false_positive_with_target_window(self, mock_focus, mock_title, mock_pag, mock_cap):
        """ensure_focus re-focuses before post_title read, preventing false positives."""
        mock_title.return_value = "My Target App"
        from tools.input_tools import do_click
        result = do_click(100, 200)
        # ensure_focus called twice: before click, and after sleep before reading post_title
        assert mock_focus.call_count == 2
        assert "navigation_warning" not in result


# ---------------------------------------------------------------------------
# Test: do_type_text (mocked pyautogui)
# ---------------------------------------------------------------------------

class TestDoTypeText:
    @mock.patch("tools.input_tools.pyautogui")
    def test_basic_type(self, mock_pag):
        from tools.input_tools import do_type_text
        result = do_type_text("hello world")
        mock_pag.write.assert_called_once_with("hello world", interval=0.02)
        assert result["action"] == "type_text"
        assert result["text"] == "hello world"

    @mock.patch("tools.input_tools.pyautogui")
    def test_custom_interval(self, mock_pag):
        from tools.input_tools import do_type_text
        result = do_type_text("abc", interval=0.05)
        mock_pag.write.assert_called_once_with("abc", interval=0.05)
        assert result["interval"] == 0.05


# ---------------------------------------------------------------------------
# Test: do_send_keys (mocked pyautogui)
# ---------------------------------------------------------------------------

class TestDoSendKeys:
    @mock.patch("tools.input_tools.pyautogui")
    def test_single_key(self, mock_pag):
        from tools.input_tools import do_send_keys
        result = do_send_keys("enter")
        mock_pag.press.assert_called_once_with("enter")
        assert result["action"] == "send_keys"

    @mock.patch("tools.input_tools.pyautogui")
    def test_hotkey_combo(self, mock_pag):
        from tools.input_tools import do_send_keys
        result = do_send_keys("ctrl+s")
        mock_pag.hotkey.assert_called_once_with("ctrl", "s")
        assert result["keys"] == "ctrl+s"

    @mock.patch("tools.input_tools.pyautogui")
    def test_complex_combo(self, mock_pag):
        from tools.input_tools import do_send_keys
        do_send_keys("ctrl+shift+p")
        mock_pag.hotkey.assert_called_once_with("ctrl", "shift", "p")


# ---------------------------------------------------------------------------
# Test: do_scroll (mocked pyautogui)
# ---------------------------------------------------------------------------

class TestDoScroll:
    # -- Explicit amount: uses mouse wheel --

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_scroll_up_wheel(self, mock_pag, mock_cap):
        from tools.input_tools import do_scroll
        result = do_scroll(500, 400, "up", amount=5)
        mock_pag.moveTo.assert_called_once_with(500, 400)
        mock_pag.scroll.assert_called_once_with(5)
        assert result["direction"] == "up"
        assert result["method"] == "wheel"
        assert result["amount"] == 5

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_scroll_down_wheel(self, mock_pag, mock_cap):
        from tools.input_tools import do_scroll
        result = do_scroll(500, 400, "down", amount=3)
        mock_pag.scroll.assert_called_once_with(-3)
        assert result["method"] == "wheel"

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_scroll_left_wheel(self, mock_pag, mock_cap):
        from tools.input_tools import do_scroll
        result = do_scroll(500, 400, "left", amount=2)
        mock_pag.hscroll.assert_called_once_with(-2)

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_scroll_right_wheel(self, mock_pag, mock_cap):
        from tools.input_tools import do_scroll
        result = do_scroll(500, 400, "right", amount=4)
        mock_pag.hscroll.assert_called_once_with(4)

    # -- Default (no amount/pages): uses PageDown/PageUp keyboard --

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_default_uses_pagedown(self, mock_pag, mock_cap):
        """When no amount or pages given, defaults to 1 PageDown press."""
        from tools.input_tools import do_scroll
        result = do_scroll(0, 0, "down")
        mock_pag.press.assert_called_once_with("pagedown")
        assert result["method"] == "keyboard"
        assert result["pages"] == 1.0

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_default_up_uses_pageup(self, mock_pag, mock_cap):
        """Default up scroll uses PageUp."""
        from tools.input_tools import do_scroll
        result = do_scroll(0, 0, "up")
        mock_pag.press.assert_called_once_with("pageup")
        assert result["method"] == "keyboard"

    # -- pages parameter: uses PageDown/PageUp keyboard --

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_pages_2_presses_twice(self, mock_pag, mock_cap):
        """pages=2 presses PageDown twice."""
        from tools.input_tools import do_scroll
        result = do_scroll(0, 0, "down", pages=2)
        calls = [c for c in mock_pag.press.call_args_list if c == mock.call("pagedown")]
        assert len(calls) == 2
        assert result["method"] == "keyboard"
        assert result["pages"] == 2

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_pages_half_uses_arrow_keys(self, mock_pag, mock_cap):
        """pages=0.5 uses arrow key presses for half-page scroll."""
        from tools.input_tools import do_scroll
        result = do_scroll(0, 0, "down", pages=0.5)
        # No full PageDown press, only arrow presses
        pagedown_calls = [c for c in mock_pag.press.call_args_list if c == mock.call("pagedown")]
        arrow_calls = [c for c in mock_pag.press.call_args_list if c == mock.call("down")]
        assert len(pagedown_calls) == 0
        assert len(arrow_calls) == 15  # int(30 * 0.5)
        assert result["method"] == "keyboard"

    # -- Horizontal scroll defaults to wheel --

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_horizontal_default_uses_wheel(self, mock_pag, mock_cap):
        """Horizontal scroll with no amount uses wheel (no keyboard equivalent)."""
        from tools.input_tools import do_scroll
        result = do_scroll(0, 0, "left")
        mock_pag.hscroll.assert_called_once_with(-50)
        assert result["method"] == "wheel"

    # -- Validation --

    @mock.patch("tools.screenshot.capture_screenshot", return_value=_FAKE_SHOT)
    @mock.patch("tools.input_tools.pyautogui")
    def test_invalid_direction_raises(self, mock_pag, mock_cap):
        from tools.input_tools import do_scroll
        with pytest.raises(ValueError):
            do_scroll(0, 0, "diagonal")


# ---------------------------------------------------------------------------
# Test: do_drag (mocked pyautogui)
# ---------------------------------------------------------------------------

class TestDoDrag:
    @mock.patch("tools.input_tools.pyautogui")
    def test_basic_drag(self, mock_pag):
        from tools.input_tools import do_drag
        result = do_drag(100, 200, 300, 400)
        mock_pag.moveTo.assert_called_once_with(100, 200)
        mock_pag.drag.assert_called_once_with(200, 200, duration=0.5)
        assert result["action"] == "drag"
        assert result["from_x"] == 100
        assert result["to_x"] == 300

    @mock.patch("tools.input_tools.pyautogui")
    def test_custom_duration(self, mock_pag):
        from tools.input_tools import do_drag
        result = do_drag(0, 0, 100, 100, duration=1.0)
        mock_pag.drag.assert_called_once_with(100, 100, duration=1.0)
        assert result["duration"] == 1.0


# ---------------------------------------------------------------------------
# Test: do_hover (mocked pyautogui)
# ---------------------------------------------------------------------------

class TestDoHover:
    @mock.patch("tools.input_tools.pyautogui")
    def test_basic_hover(self, mock_pag):
        from tools.input_tools import do_hover
        result = do_hover(500, 300)
        mock_pag.moveTo.assert_called_once_with(500, 300)
        assert result["action"] == "hover"
        assert result["x"] == 500
        assert result["y"] == 300


# ---------------------------------------------------------------------------
# Test: register (tool count)
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_returns_seven(self):
        from tools.input_tools import register

        mock_server = mock.MagicMock()
        # server.tool() returns a decorator, which returns the function
        mock_server.tool.return_value = lambda fn: fn
        count = register(mock_server)
        assert count == 7
        assert mock_server.tool.call_count == 7

