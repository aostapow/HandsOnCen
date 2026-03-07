"""Integration test: Accessibility element targeting."""

import time
import pytest


class TestElementTargeting:
    def test_find_notepad_menu(self):
        from tools.windows import do_launch_app, do_focus_window
        from tools.ui_automation import do_find_element, do_click_element
        import pyautogui

        # Launch Notepad
        result = do_launch_app("notepad.exe")
        assert result["success"]
        time.sleep(1)

        do_focus_window("Notepad", action="focus")
        time.sleep(0.3)

        # Find File menu via accessibility
        result = do_find_element(name="File", role="MenuItem", window_title="Notepad")
        assert result["found"]
        assert result["elements"][0]["name"] == "File"

        # Click it
        click_result = do_click_element(name="File", role="MenuItem", window_title="Notepad")
        assert click_result["success"]
        time.sleep(0.5)

        # Verify menu opened -- "New" should now be visible
        new_item = do_find_element(name="New", window_title="Notepad")
        assert new_item["found"]

        # Close menu and Notepad
        pyautogui.press("escape")
        time.sleep(0.2)
        pyautogui.hotkey("alt", "F4")

