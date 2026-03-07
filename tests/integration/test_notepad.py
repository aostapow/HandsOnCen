"""Integration test: Notepad type + clipboard verify."""

import time
import subprocess
import pytest


class TestNotepadType:
    def test_type_and_read_back(self):
        from tools.windows import do_launch_app, do_focus_window
        from tools.input_tools import do_type_text
        from tools.manage import do_clipboard_read, do_clipboard_write
        import pyautogui

        # Launch Notepad
        result = do_launch_app("notepad.exe")
        assert result["success"]
        time.sleep(1)

        # Focus it
        do_focus_window("Notepad", action="focus")
        time.sleep(0.3)

        # Type text
        test_text = "Hello from HandsOn integration test!"
        do_type_text(test_text)
        time.sleep(0.3)

        # Select all + copy
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.1)

        # Verify clipboard
        clipboard = do_clipboard_read()
        assert test_text in clipboard

        # Close without saving
        pyautogui.hotkey("alt", "F4")
        time.sleep(0.3)
        pyautogui.press("tab")  # Focus "Don't Save"
        time.sleep(0.1)
        pyautogui.press("enter")

