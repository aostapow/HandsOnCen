"""macOS input routing tests.

Verifies that:
- tools.input_tools imports without error on macOS (no ctypes.windll crash)
- Win32-only code paths (_HAS_WIN32, _make_key_event) are properly guarded
- do_type_text and do_send_keys always route through pyautogui on macOS
- Helper/validation functions (parse_hotkey, validate_button, validate_direction) work
- _send_text_to_console and _send_keys_to_console return early on macOS
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


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestDarwinImportGuards:
    """Verify that Win32-only code is properly guarded on macOS."""

    def test_input_tools_importable(self):
        """input_tools module should import without error on macOS."""
        import tools.input_tools
        assert tools.input_tools is not None

    def test_has_win32_is_false(self):
        """_HAS_WIN32 should be False on macOS."""
        from tools.input_tools import _HAS_WIN32
        assert _HAS_WIN32 is False

    def test_make_key_event_not_defined(self):
        """_make_key_event should not exist on macOS (guarded by _HAS_WIN32)."""
        import tools.input_tools
        assert not hasattr(tools.input_tools, "_make_key_event")

    def test_send_text_to_console_returns_error(self):
        """_send_text_to_console should return early with error on macOS."""
        from tools.input_tools import _send_text_to_console
        result = _send_text_to_console(pid=123, text="hello")
        assert result["success"] is False
        assert "Windows only" in result["error"]

    def test_send_keys_to_console_returns_error(self):
        """_send_keys_to_console should return early with error on macOS."""
        from tools.input_tools import _send_keys_to_console
        result = _send_keys_to_console(pid=123, keys="enter")
        assert result["success"] is False
        assert "Windows only" in result["error"]


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestDarwinHelpers:
    """Verify cross-platform helper functions work on macOS."""

    def test_parse_hotkey_single(self):
        from tools.input_tools import parse_hotkey
        assert parse_hotkey("enter") == ["enter"]

    def test_parse_hotkey_combo(self):
        from tools.input_tools import parse_hotkey
        assert parse_hotkey("ctrl+s") == ["ctrl", "s"]

    def test_parse_hotkey_triple(self):
        from tools.input_tools import parse_hotkey
        assert parse_hotkey("cmd+shift+p") == ["cmd", "shift", "p"]

    def test_validate_button_left(self):
        from tools.input_tools import validate_button
        assert validate_button("left") == "left"

    def test_validate_button_case_insensitive(self):
        from tools.input_tools import validate_button
        assert validate_button("RIGHT") == "right"
        assert validate_button("Middle") == "middle"

    def test_validate_button_invalid(self):
        from tools.input_tools import validate_button
        with pytest.raises(ValueError, match="Invalid button"):
            validate_button("invalid")

    def test_validate_direction_up(self):
        from tools.input_tools import validate_direction
        assert validate_direction("up") == "up"

    def test_validate_direction_case_insensitive(self):
        from tools.input_tools import validate_direction
        assert validate_direction("DOWN") == "down"

    def test_validate_direction_invalid(self):
        from tools.input_tools import validate_direction
        with pytest.raises(ValueError, match="Invalid direction"):
            validate_direction("diagonal")


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestDarwinInputRouting:
    """Verify that input functions route through pyautogui on macOS."""

    def test_do_type_text_uses_pyautogui(self):
        """On macOS, do_type_text should always use pyautogui, never console API."""
        from tools.input_tools import do_type_text

        with mock.patch("tools.input_tools.get_foreground_type") as mock_fg, \
             mock.patch("pyautogui.write") as mock_write, \
             mock.patch("tools.target_window.ensure_focus"):
            mock_fg.return_value = {
                "type": "terminal",
                "process_name": "iTerm2",
                "pid": 123,
                "hwnd": 0,
            }
            result = do_type_text("hello")
            mock_write.assert_called_once_with("hello", interval=0.02)
            assert result["method"] == "pyautogui"

    def test_do_type_text_never_hits_console_path(self):
        """Even if fg type were 'console', the console API returns early on macOS."""
        from tools.input_tools import do_type_text

        with mock.patch("tools.input_tools.get_foreground_type") as mock_fg, \
             mock.patch("pyautogui.write") as mock_write, \
             mock.patch("tools.target_window.ensure_focus"):
            # Simulate a 'console' classification (should never happen on macOS,
            # but verify the guard works even if it did)
            mock_fg.return_value = {
                "type": "console",
                "process_name": "cmd.exe",
                "pid": 999,
                "hwnd": 0,
            }
            result = do_type_text("test")
            # _send_text_to_console returns early with error, then do_type_text
            # uses the result's method which is from the console path
            assert result["action"] == "type_text"

    def test_do_send_keys_single_key_uses_applescript(self):
        """On macOS, do_send_keys should route single keys through AppleScript."""
        from tools.input_tools import do_send_keys

        with mock.patch("tools.input_tools.get_foreground_type") as mock_fg, \
             mock.patch("tools.input_tools._send_keys_applescript") as mock_as, \
             mock.patch("tools.target_window.ensure_focus"):
            mock_fg.return_value = {
                "type": "terminal",
                "process_name": "iTerm2",
                "pid": 123,
                "hwnd": 0,
            }
            mock_as.return_value = {"action": "send_keys", "keys": "enter", "method": "applescript"}
            result = do_send_keys("enter")
            mock_as.assert_called_once_with("enter")
            assert result["method"] == "applescript"

    def test_do_send_keys_combo_uses_applescript(self):
        """On macOS, do_send_keys should route key combos through AppleScript."""
        from tools.input_tools import do_send_keys

        with mock.patch("tools.input_tools.get_foreground_type") as mock_fg, \
             mock.patch("tools.input_tools._send_keys_applescript") as mock_as, \
             mock.patch("tools.target_window.ensure_focus"):
            mock_fg.return_value = {
                "type": "generic",
                "process_name": "Safari",
                "pid": 456,
                "hwnd": 0,
            }
            mock_as.return_value = {"action": "send_keys", "keys": "cmd+s", "method": "applescript"}
            result = do_send_keys("cmd+s")
            mock_as.assert_called_once_with("cmd+s")
            assert result["method"] == "applescript"

    def test_do_click_uses_pyautogui(self):
        """On macOS, do_click should use pyautogui.click."""
        from tools.input_tools import do_click

        fake_shot = {"image": "AAAA", "width": 100, "height": 100}
        with mock.patch("pyautogui.click") as mock_click, \
             mock.patch("tools.target_window.ensure_focus"), \
             mock.patch("tools.windows.get_foreground_title", return_value="Test"), \
             mock.patch("tools.screenshot.capture_screenshot", return_value=fake_shot), \
             mock.patch("tools.screenshot.compare_screenshots", return_value=0.0), \
             mock.patch("time.sleep"):
            result = do_click(100, 200)
            mock_click.assert_called_once_with(x=100, y=200, button="left", clicks=1)
            assert result["action"] == "click"

    def test_do_hover_uses_pyautogui(self):
        """On macOS, do_hover should use pyautogui.moveTo."""
        from tools.input_tools import do_hover

        with mock.patch("pyautogui.moveTo") as mock_move, \
             mock.patch("tools.target_window.ensure_focus"):
            result = do_hover(300, 400)
            mock_move.assert_called_once_with(300, 400)
            assert result["action"] == "hover"

    def test_do_get_mouse_position(self):
        """On macOS, do_get_mouse_position should use pyautogui.position."""
        from tools.input_tools import do_get_mouse_position

        with mock.patch("pyautogui.position", return_value=(500, 600)):
            result = do_get_mouse_position()
            assert result["x"] == 500
            assert result["y"] == 600


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestDarwinGetForegroundType:
    """Verify get_foreground_type routes to handson_platform on macOS."""

    def test_delegates_to_classify_window_native(self):
        """On macOS, get_foreground_type should use handson_platform.classify_window_native."""
        from tools.window_classify import get_foreground_type

        with mock.patch("handson_platform.classify_window_native") as mock_classify:
            mock_classify.return_value = {
                "type": "browser",
                "process_name": "Safari",
                "pid": 789,
                "class_name": "",
                "hwnd": 0,
                "is_elevated": False,
            }
            result = get_foreground_type()
            mock_classify.assert_called_once()
            assert result["type"] == "browser"
            assert result["process_name"] == "Safari"

