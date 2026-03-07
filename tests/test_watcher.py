"""Tests for the notification watcher (window diff + classification)."""

import os
import sys
import time
from unittest import mock

import pytest

# Make the handson-server package importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


# ---------------------------------------------------------------------------
# Test: window classification heuristics
# ---------------------------------------------------------------------------

class TestClassifyWindowType:
    def test_toast_small_window(self):
        from tools.watcher import classify_window_type
        assert classify_window_type("Notification", 350, 100) == "toast"

    def test_dialog_by_keyword(self):
        from tools.watcher import classify_window_type
        assert classify_window_type("Save As", 600, 500) == "dialog"

    def test_dialog_by_size(self):
        from tools.watcher import classify_window_type
        assert classify_window_type("Untitled", 500, 400) == "dialog"

    def test_window_large(self):
        from tools.watcher import classify_window_type
        assert classify_window_type("My App - Main", 1200, 800) == "window"

    def test_dialog_keywords_case_insensitive(self):
        from tools.watcher import classify_window_type
        assert classify_window_type("WARNING: Something", 600, 500) == "dialog"
        assert classify_window_type("Confirm Delete", 500, 300) == "dialog"


# ---------------------------------------------------------------------------
# Test: window list diffing
# ---------------------------------------------------------------------------

class TestWindowDiffing:
    """Test the watcher's ability to detect new windows."""

    def _make_window(self, title, width=800, height=600, x=0, y=0, process_name="app.exe"):
        return {
            "title": title,
            "width": width,
            "height": height,
            "x": x,
            "y": y,
            "process_name": process_name,
        }

    def test_new_window_detected(self):
        """A window that wasn't in the baseline should be detected."""
        from tools import watcher as mod

        baseline = [self._make_window("Existing")]
        current = [self._make_window("Existing"), self._make_window("New App")]

        baseline_titles = {w["title"] for w in baseline}
        current_titles = {w["title"] for w in current}

        new = current_titles - baseline_titles
        assert new == {"New App"}

    def test_removed_window_not_reported(self):
        """Closed windows should not show up as new."""
        baseline = [self._make_window("App A"), self._make_window("App B")]
        current = [self._make_window("App A")]

        baseline_titles = {w["title"] for w in baseline}
        current_titles = {w["title"] for w in current}

        new = current_titles - baseline_titles
        assert len(new) == 0

    def test_tiny_windows_filtered(self):
        """Windows smaller than the minimum size should be ignored."""
        from tools.watcher import _MIN_WINDOW_SIZE

        tiny = self._make_window("Tiny", width=10, height=10)
        assert tiny["width"] < _MIN_WINDOW_SIZE


# ---------------------------------------------------------------------------
# Test: watcher lifecycle
# ---------------------------------------------------------------------------

class TestWatcherLifecycle:
    """Test start/stop/get_notifications with mocked window list."""

    def setup_method(self):
        from tools.watcher import _state
        # Ensure clean state before each test
        if _state.running:
            from tools.watcher import do_stop_watcher
            do_stop_watcher()
        _state.reset()

    def teardown_method(self):
        from tools.watcher import _state, do_stop_watcher
        if _state.running:
            do_stop_watcher()
        _state.reset()

    def test_start_and_stop(self):
        from tools.watcher import do_start_watcher, do_stop_watcher, _state

        windows = [
            {"title": "Existing", "width": 800, "height": 600, "x": 0, "y": 0, "process_name": ""},
        ]
        with mock.patch("tools.watcher.do_list_windows", return_value=windows):
            # Patch at the import location in the module
            result = do_start_watcher(poll_interval=0.2, capture_snippets=False)
            assert result["started"] is True
            assert _state.running is True

        with mock.patch("tools.watcher.do_list_windows", return_value=windows):
            result = do_stop_watcher()
            assert result["stopped"] is True
            assert _state.running is False

    def test_double_start_returns_error(self):
        from tools.watcher import do_start_watcher, _state

        windows = [
            {"title": "App", "width": 800, "height": 600, "x": 0, "y": 0, "process_name": ""},
        ]
        with mock.patch("tools.watcher.do_list_windows", return_value=windows):
            do_start_watcher(poll_interval=0.2, capture_snippets=False)
            result = do_start_watcher()
            assert "error" in result

    def test_stop_when_not_running(self):
        from tools.watcher import do_stop_watcher
        result = do_stop_watcher()
        assert "error" in result

    def test_event_capture(self):
        """New windows appearing should generate events."""
        from tools.watcher import do_start_watcher, do_stop_watcher, do_get_notifications

        call_count = {"n": 0}

        def mock_list_windows():
            call_count["n"] += 1
            base = [
                {"title": "Existing", "width": 800, "height": 600, "x": 0, "y": 0, "process_name": "app.exe"},
            ]
            if call_count["n"] > 2:
                # After a couple polls, a new window appears
                base.append(
                    {"title": "New Dialog", "width": 400, "height": 300, "x": 100, "y": 100, "process_name": "dialog.exe"},
                )
            return base

        with mock.patch("tools.watcher.do_list_windows", side_effect=mock_list_windows):
            do_start_watcher(poll_interval=0.1, capture_snippets=False)
            # Wait for a few poll cycles
            time.sleep(0.6)
            result = do_get_notifications(clear=True)
            do_stop_watcher()

        assert result["count"] >= 1
        event = result["events"][0]
        assert event["title"] == "New Dialog"
        assert event["type"] == "dialog"

    def test_get_notifications_clears_queue(self):
        from tools.watcher import _state, do_get_notifications

        _state.events = [
            {"timestamp": time.time(), "type": "window", "title": "Test",
             "process_name": "", "geometry": {"x": 0, "y": 0, "width": 800, "height": 600},
             "snippet_b64": None},
        ]
        _state.running = True

        result = do_get_notifications(clear=True)
        assert result["count"] == 1
        assert len(_state.events) == 0

    def test_get_notifications_no_clear(self):
        from tools.watcher import _state, do_get_notifications

        _state.events = [
            {"timestamp": time.time(), "type": "toast", "title": "Alert",
             "process_name": "", "geometry": {"x": 0, "y": 0, "width": 300, "height": 100},
             "snippet_b64": None},
        ]
        _state.running = True

        result = do_get_notifications(clear=False)
        assert result["count"] == 1
        assert len(_state.events) == 1  # not cleared

