"""Tests for the window tools (list_windows, focus_window, launch_app).

Validates helper/validation functions, core function behaviour with mocked
platform-specific APIs, and MCP tool registration.
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
# Test: get_platform
# ---------------------------------------------------------------------------

class TestPlatformDetection:
    def test_get_platform_returns_known_value(self):
        from tools.windows import get_platform
        plat = get_platform()
        assert plat in ("windows", "darwin", "linux")

    def test_get_platform_windows(self):
        from tools.windows import get_platform
        with mock.patch("tools.windows.platform.system", return_value="Windows"):
            assert get_platform() == "windows"

    def test_get_platform_darwin(self):
        from tools.windows import get_platform
        with mock.patch("tools.windows.platform.system", return_value="Darwin"):
            assert get_platform() == "darwin"

    def test_get_platform_linux(self):
        from tools.windows import get_platform
        with mock.patch("tools.windows.platform.system", return_value="Linux"):
            assert get_platform() == "linux"

    def test_get_platform_unknown_falls_to_linux(self):
        """Unknown platform strings should fall back to 'linux'."""
        from tools.windows import get_platform
        with mock.patch("tools.windows.platform.system", return_value="FreeBSD"):
            assert get_platform() == "linux"


# ---------------------------------------------------------------------------
# Test: validate_window_action
# ---------------------------------------------------------------------------

class TestActionValidation:
    def test_valid_actions(self):
        from tools.windows import validate_window_action
        for action in ("focus", "minimize", "maximize", "restore"):
            assert validate_window_action(action) == action

    def test_case_insensitive(self):
        from tools.windows import validate_window_action
        assert validate_window_action("FOCUS") == "focus"
        assert validate_window_action("Minimize") == "minimize"
        assert validate_window_action("MAXIMIZE") == "maximize"
        assert validate_window_action("Restore") == "restore"

    def test_invalid_action_raises(self):
        from tools.windows import validate_window_action
        with pytest.raises(ValueError):
            validate_window_action("destroy")

    def test_empty_string_raises(self):
        from tools.windows import validate_window_action
        with pytest.raises(ValueError):
            validate_window_action("")


# ---------------------------------------------------------------------------
# Test: do_list_windows (mocked platform calls)
# ---------------------------------------------------------------------------

class TestDoListWindows:
    @mock.patch("tools.windows.get_platform", return_value="windows")
    @mock.patch("tools.windows._list_windows_win32")
    def test_dispatches_to_win32(self, mock_win32, mock_plat):
        from tools.windows import do_list_windows
        mock_win32.return_value = [
            {"title": "Notepad", "x": 0, "y": 0, "width": 800, "height": 600},
        ]
        result = do_list_windows()
        mock_win32.assert_called_once()
        assert len(result) == 1
        assert result[0]["title"] == "Notepad"

    @mock.patch("tools.windows.get_platform", return_value="darwin")
    @mock.patch("handson_platform.list_windows_native")
    def test_dispatches_to_darwin(self, mock_darwin, mock_plat):
        from tools.windows import do_list_windows
        mock_darwin.return_value = [
            {"title": "Safari", "x": 10, "y": 20, "width": 1024, "height": 768},
        ]
        result = do_list_windows()
        mock_darwin.assert_called_once()
        assert result[0]["title"] == "Safari"

    @mock.patch("tools.windows.get_platform", return_value="linux")
    @mock.patch("tools.windows._list_windows_linux")
    def test_dispatches_to_linux(self, mock_linux, mock_plat):
        from tools.windows import do_list_windows
        mock_linux.return_value = [
            {"title": "Terminal", "x": 50, "y": 50, "width": 640, "height": 480},
        ]
        result = do_list_windows()
        mock_linux.assert_called_once()
        assert result[0]["title"] == "Terminal"

    @mock.patch("tools.windows.get_platform", return_value="windows")
    @mock.patch("tools.windows._list_windows_win32")
    def test_returns_list_of_dicts(self, mock_win32, mock_plat):
        from tools.windows import do_list_windows
        mock_win32.return_value = [
            {"title": "A", "x": 0, "y": 0, "width": 100, "height": 100},
            {"title": "B", "x": 10, "y": 10, "width": 200, "height": 200},
        ]
        result = do_list_windows()
        assert isinstance(result, list)
        for item in result:
            assert "title" in item
            assert "x" in item
            assert "y" in item
            assert "width" in item
            assert "height" in item


# ---------------------------------------------------------------------------
# Test: do_focus_window (mocked platform calls)
# ---------------------------------------------------------------------------

class TestDoFocusWindow:
    @mock.patch("tools.windows.get_platform", return_value="windows")
    @mock.patch("tools.windows._focus_window_win32")
    def test_focus_success(self, mock_focus, mock_plat):
        from tools.windows import do_focus_window
        mock_focus.return_value = {
            "success": True, "window": "Notepad", "action": "focus"
        }
        result = do_focus_window("Notepad")
        mock_focus.assert_called_once_with("Notepad", "focus")
        assert result["success"] is True

    @mock.patch("tools.windows.get_platform", return_value="windows")
    @mock.patch("tools.windows._focus_window_win32")
    def test_focus_with_action(self, mock_focus, mock_plat):
        from tools.windows import do_focus_window
        mock_focus.return_value = {
            "success": True, "window": "Notepad", "action": "minimize"
        }
        result = do_focus_window("Notepad", action="minimize")
        mock_focus.assert_called_once_with("Notepad", "minimize")
        assert result["action"] == "minimize"

    def test_invalid_action_raises(self):
        from tools.windows import do_focus_window
        with pytest.raises(ValueError):
            do_focus_window("Notepad", action="destroy")

    @mock.patch("tools.windows.get_platform", return_value="darwin")
    @mock.patch("handson_platform.focus_window_native")
    def test_dispatches_to_darwin(self, mock_focus, mock_plat):
        from tools.windows import do_focus_window
        mock_focus.return_value = {
            "success": True, "window": "Safari", "action": "focus"
        }
        result = do_focus_window("Safari")
        mock_focus.assert_called_once_with("Safari", "focus")
        assert result["success"] is True

    @mock.patch("tools.windows.get_platform", return_value="linux")
    @mock.patch("tools.windows._focus_window_linux")
    def test_dispatches_to_linux(self, mock_focus, mock_plat):
        from tools.windows import do_focus_window
        mock_focus.return_value = {
            "success": True, "window": "Terminal", "action": "focus"
        }
        result = do_focus_window("Terminal")
        mock_focus.assert_called_once_with("Terminal", "focus")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Test: do_launch_app (mocked subprocess)
# ---------------------------------------------------------------------------

class TestDoLaunchApp:
    @mock.patch("tools.windows.subprocess.Popen")
    def test_launch_success(self, mock_popen):
        from tools.windows import do_launch_app
        mock_proc = mock.MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        result = do_launch_app("notepad.exe")
        mock_popen.assert_called_once()
        assert result["success"] is True
        assert result["pid"] == 12345

    @mock.patch("tools.windows.subprocess.Popen")
    def test_launch_with_args(self, mock_popen):
        from tools.windows import do_launch_app
        mock_proc = mock.MagicMock()
        mock_proc.pid = 54321
        mock_popen.return_value = mock_proc
        result = do_launch_app("notepad.exe", args="test.txt")
        call_args = mock_popen.call_args
        # The command should include args
        cmd = call_args[0][0]
        assert "notepad.exe" in cmd
        assert "test.txt" in cmd
        assert result["success"] is True
        assert result["pid"] == 54321

    @mock.patch("tools.windows.subprocess.Popen")
    def test_launch_with_empty_args(self, mock_popen):
        from tools.windows import do_launch_app
        mock_proc = mock.MagicMock()
        mock_proc.pid = 99
        mock_popen.return_value = mock_proc
        result = do_launch_app("calc.exe", args="")
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd == ["calc.exe"]
        assert result["success"] is True

    @mock.patch("tools.windows.subprocess.Popen")
    def test_launch_failure(self, mock_popen):
        from tools.windows import do_launch_app
        mock_popen.side_effect = FileNotFoundError("No such file: fake.exe")
        result = do_launch_app("fake.exe")
        assert result["success"] is False
        assert "error" in result

    @mock.patch("tools.windows.subprocess.Popen")
    def test_launch_os_error(self, mock_popen):
        from tools.windows import do_launch_app
        mock_popen.side_effect = OSError("Permission denied")
        result = do_launch_app("restricted.exe")
        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Test: register (tool count)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Test: find_matching_window
# ---------------------------------------------------------------------------

class TestFindMatchingWindow:
    """Tests for the window matching helper."""

    def _windows(self):
        return [
            {"title": "Submit to r/ClaudeCode and 9 more pages - Personal - Microsoft Edge", "x": 0, "y": 0, "width": 1920, "height": 1080},
            {"title": "Claude Code", "x": 0, "y": 0, "width": 800, "height": 600},
            {"title": "Untitled - Notepad", "x": 100, "y": 100, "width": 640, "height": 480},
        ]

    def test_exact_substring_match(self):
        from tools.windows import find_matching_window
        result = find_matching_window("Edge", self._windows())
        assert result["window"] is not None
        assert "Edge" in result["window"]["title"]
        assert result["match_quality"] == "exact"

    def test_submit_is_exact_substring(self):
        """'Submit' appears in the full title, so it matches as 'exact'."""
        from tools.windows import find_matching_window
        result = find_matching_window("Submit", self._windows())
        assert result["window"] is not None
        assert result["match_quality"] == "exact"

    def test_reddit_not_in_title(self):
        """'Reddit' is NOT in 'r/ClaudeCode' -- no match expected."""
        from tools.windows import find_matching_window
        result = find_matching_window("Reddit", self._windows())
        assert result["window"] is None
        assert len(result["available"]) == 3

    def test_case_insensitive(self):
        from tools.windows import find_matching_window
        result = find_matching_window("edge", self._windows())
        assert result["window"] is not None

    def test_no_match_returns_available(self):
        from tools.windows import find_matching_window
        result = find_matching_window("Firefox", self._windows())
        assert result["window"] is None
        assert "available" in result
        assert len(result["available"]) == 3

    def test_empty_windows_list(self):
        from tools.windows import find_matching_window
        result = find_matching_window("Edge", [])
        assert result["window"] is None
        assert result["available"] == []

    def test_notepad_exact_match(self):
        from tools.windows import find_matching_window
        result = find_matching_window("Notepad", self._windows())
        assert result["window"] is not None
        assert result["match_quality"] == "exact"

    def test_available_lists_all_titles(self):
        """On no match, available should contain all window titles."""
        from tools.windows import find_matching_window
        result = find_matching_window("NonexistentApp", self._windows())
        assert result["window"] is None
        titles = result["available"]
        assert "Claude Code" in titles
        assert "Untitled - Notepad" in titles
        assert any("Microsoft Edge" in t for t in titles)

    def test_claude_code_match(self):
        from tools.windows import find_matching_window
        result = find_matching_window("Claude Code", self._windows())
        assert result["window"] is not None
        assert result["window"]["title"] == "Claude Code"
        assert result["match_quality"] == "exact"


class TestProcessNameFallback:
    """Tests for process-name fallback in find_matching_window."""

    def _windows_with_process(self):
        return [
            {"title": "Main Window", "process_name": "steam.exe", "x": 0, "y": 0, "width": 1920, "height": 1080},
            {"title": "Claude Code", "process_name": "claude.exe", "x": 0, "y": 0, "width": 800, "height": 600},
            {"title": "Untitled - Notepad", "process_name": "notepad.exe", "x": 100, "y": 100, "width": 640, "height": 480},
        ]

    def test_process_name_fallback_matches(self):
        """Query 'steam' should match process 'steam.exe' when title doesn't match."""
        from tools.windows import find_matching_window
        result = find_matching_window("steam", self._windows_with_process())
        assert result["window"] is not None
        assert result["window"]["title"] == "Main Window"
        assert result["match_quality"] == "process_name"

    def test_title_match_preferred_over_process(self):
        """Title substring match should be preferred over process-name match."""
        from tools.windows import find_matching_window
        result = find_matching_window("Notepad", self._windows_with_process())
        assert result["window"] is not None
        assert result["match_quality"] == "exact"  # Not process_name

    def test_process_name_case_insensitive(self):
        from tools.windows import find_matching_window
        result = find_matching_window("Steam", self._windows_with_process())
        assert result["window"] is not None
        assert result["match_quality"] == "process_name"

    def test_no_process_name_key_is_safe(self):
        """Windows without process_name key should be skipped gracefully."""
        from tools.windows import find_matching_window
        windows = [
            {"title": "Old Window", "x": 0, "y": 0, "width": 100, "height": 100},
        ]
        result = find_matching_window("myapp", windows)
        assert result["window"] is None

    def test_process_name_partial_match(self):
        """Partial process name match should work (e.g. 'note' in 'notepad')."""
        from tools.windows import find_matching_window
        result = find_matching_window("note", self._windows_with_process())
        # "note" is in "Untitled - Notepad" title, so should match by title first
        assert result["window"] is not None
        assert result["match_quality"] == "exact"


class TestGetForegroundTitle:
    @mock.patch("tools.windows.get_platform", return_value="windows")
    def test_returns_title_string(self, _mock_plat):
        """get_foreground_title returns a string (possibly empty)."""
        from tools.windows import get_foreground_title
        with mock.patch("ctypes.windll.user32") as mock_user32:
            mock_user32.GetForegroundWindow.return_value = 12345
            mock_user32.GetWindowTextLengthW.return_value = 10
            mock_user32.GetWindowTextW.side_effect = lambda hwnd, buf, n: None
            result = get_foreground_title()
            assert isinstance(result, str)

    @mock.patch("tools.windows.get_platform", return_value="linux")
    def test_returns_empty_on_non_windows(self, _mock_plat):
        from tools.windows import get_foreground_title
        assert get_foreground_title() == ""


class TestRegister:
    def test_register_returns_three(self):
        from tools.windows import register
        mock_server = mock.MagicMock()
        mock_server.tool.return_value = lambda fn: fn
        count = register(mock_server)
        assert count == 3
        assert mock_server.tool.call_count == 3

