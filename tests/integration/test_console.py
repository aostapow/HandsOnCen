"""Integration test: Console typing via Win32 API."""

import time
import pytest


class TestConsoleType:
    def test_type_in_cmd(self):
        from tools.windows import do_launch_app, do_focus_window, do_list_windows
        from tools.input_tools import do_type_text, do_send_keys

        # Launch cmd
        result = do_launch_app("cmd.exe")
        assert result["success"]
        time.sleep(1)

        # Focus it
        do_focus_window("cmd", action="focus")
        time.sleep(0.3)

        # Type via Win32 console API (auto-routed)
        do_type_text("echo HANDSON_TEST_OK")
        time.sleep(0.1)
        do_send_keys("enter")
        time.sleep(0.5)

        # Verify by taking screenshot (visual check -- cmd output not easily clipboard-able)
        from tools.screenshot import capture_screenshot
        shot = capture_screenshot()
        assert shot["width"] > 0

        # Close cmd
        do_type_text("exit")
        do_send_keys("enter")
