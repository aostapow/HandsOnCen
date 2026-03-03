# tests/test_ui_automation.py
"""Tests for UI Automation accessibility targeting."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestFindElement:
    @mock.patch("tools.ui_automation._get_desktop")
    def test_find_by_name(self, mock_desktop):
        mock_elem = mock.MagicMock()
        mock_elem.element_info.name = "File"
        mock_elem.element_info.control_type = "MenuItem"
        mock_elem.element_info.rectangle = mock.MagicMock(
            left=10, top=20, right=110, bottom=50
        )
        mock_elem.element_info.rich_text = ""

        mock_window = mock.MagicMock()
        mock_window.descendants.return_value = [mock_elem]
        mock_desktop.return_value.windows.return_value = [mock_window]
        mock_window.window_text.return_value = "Untitled - Notepad"

        from tools.ui_automation import do_find_element
        result = do_find_element(name="File", window_title="Notepad")

        assert result["found"] is True
        assert result["elements"][0]["name"] == "File"
        assert result["elements"][0]["role"] == "MenuItem"
        assert result["elements"][0]["x"] == 10
        assert result["elements"][0]["width"] == 100

    @mock.patch("tools.ui_automation._get_desktop")
    def test_find_no_match(self, mock_desktop):
        mock_window = mock.MagicMock()
        mock_window.descendants.return_value = []
        mock_desktop.return_value.windows.return_value = [mock_window]
        mock_window.window_text.return_value = "Untitled - Notepad"

        from tools.ui_automation import do_find_element
        result = do_find_element(name="NonExistent", window_title="Notepad")

        assert result["found"] is False


class TestClickElement:
    @mock.patch("tools.ui_automation.do_click")
    @mock.patch("tools.ui_automation.do_find_element")
    def test_click_found_element(self, mock_find, mock_click):
        mock_find.return_value = {
            "found": True,
            "elements": [{"name": "OK", "role": "Button", "x": 100, "y": 200, "width": 80, "height": 30}]
        }
        mock_click.return_value = {"action": "click", "x": 140, "y": 215}

        from tools.ui_automation import do_click_element
        result = do_click_element(name="OK", window_title="Dialog")

        # Should click center of element: x=100+80/2=140, y=200+30/2=215
        mock_click.assert_called_once_with(140, 215)

    @mock.patch("tools.ui_automation._fuzzy_find_nearest", return_value=None)
    @mock.patch("tools.ui_automation.do_find_element")
    def test_click_not_found(self, mock_find, mock_fuzzy):
        mock_find.return_value = {"found": False, "elements": []}

        from tools.ui_automation import do_click_element
        result = do_click_element(name="Ghost", window_title="Nowhere")

        assert result["success"] is False


class TestListElements:
    @mock.patch("tools.ui_automation._get_desktop")
    def test_list_returns_tree(self, mock_desktop):
        mock_elem1 = mock.MagicMock()
        mock_elem1.element_info.name = "File"
        mock_elem1.element_info.control_type = "MenuItem"
        mock_elem1.element_info.rectangle = mock.MagicMock(left=0, top=0, right=50, bottom=25)
        mock_elem1.element_info.rich_text = ""

        mock_elem2 = mock.MagicMock()
        mock_elem2.element_info.name = "Edit"
        mock_elem2.element_info.control_type = "MenuItem"
        mock_elem2.element_info.rectangle = mock.MagicMock(left=50, top=0, right=100, bottom=25)
        mock_elem2.element_info.rich_text = ""

        mock_window = mock.MagicMock()
        mock_window.descendants.return_value = [mock_elem1, mock_elem2]
        mock_desktop.return_value.windows.return_value = [mock_window]
        mock_window.window_text.return_value = "Notepad"

        from tools.ui_automation import do_list_elements
        result = do_list_elements(window_title="Notepad")

        assert len(result["elements"]) == 2
        assert result["elements"][0]["name"] == "File"
        assert result["elements"][1]["name"] == "Edit"


class TestListElementsRoleFilter:
    @mock.patch("tools.ui_automation._get_desktop")
    def test_role_filter_returns_only_matching_type(self, mock_desktop):
        mock_spinner = mock.MagicMock()
        mock_spinner.element_info.name = "Amount"
        mock_spinner.element_info.control_type = "Spinner"
        mock_spinner.element_info.rectangle = mock.MagicMock(left=100, top=200, right=200, bottom=230)
        mock_spinner.element_info.rich_text = "42"

        mock_button = mock.MagicMock()
        mock_button.element_info.name = "OK"
        mock_button.element_info.control_type = "Button"
        mock_button.element_info.rectangle = mock.MagicMock(left=300, top=400, right=380, bottom=430)
        mock_button.element_info.rich_text = ""

        mock_window = mock.MagicMock()
        # When role filter is set, descendants() is called with no depth limit
        mock_window.descendants.return_value = [mock_spinner, mock_button]
        mock_desktop.return_value.windows.return_value = [mock_window]

        from tools.ui_automation import do_list_elements
        result = do_list_elements(role="Spinner")

        assert len(result["elements"]) == 1
        assert result["elements"][0]["name"] == "Amount"
        assert result["elements"][0]["role"] == "Spinner"
        # When role is set, descendants() should be called WITHOUT depth arg
        mock_window.descendants.assert_called_once_with()

    @mock.patch("tools.ui_automation._get_desktop")
    def test_no_role_uses_max_depth(self, mock_desktop):
        mock_window = mock.MagicMock()
        mock_window.descendants.return_value = []
        mock_desktop.return_value.windows.return_value = [mock_window]

        from tools.ui_automation import do_list_elements
        result = do_list_elements(max_depth=5)

        mock_window.descendants.assert_called_once_with(depth=5)


class TestGetFocusedElement:
    @mock.patch("tools.ui_automation._get_desktop")
    def test_returns_focused_element(self, mock_desktop):
        mock_elem = mock.MagicMock()
        mock_elem.element_info.name = "Username"
        mock_elem.element_info.control_type = "Edit"
        mock_elem.element_info.rectangle = mock.MagicMock(
            left=100, top=200, right=300, bottom=230
        )
        mock_elem.element_info.rich_text = "admin"
        mock_desktop.return_value.get_focus.return_value = mock_elem

        from tools.ui_automation import do_get_focused_element
        result = do_get_focused_element()

        assert result["found"] is True
        assert result["element"]["name"] == "Username"
        assert result["element"]["role"] == "Edit"
        assert result["element"]["value"] == "admin"

    @mock.patch("tools.ui_automation._get_desktop")
    def test_returns_not_found_on_exception(self, mock_desktop):
        mock_desktop.return_value.get_focus.side_effect = Exception("UIA unavailable")

        from tools.ui_automation import do_get_focused_element
        result = do_get_focused_element()

        assert result["found"] is False


class TestSmartFind:
    @mock.patch("tools.ocr.do_find_text")
    @mock.patch("tools.ui_automation.do_find_element")
    def test_uia_found_returns_uia(self, mock_uia, mock_ocr):
        mock_uia.return_value = {
            "found": True,
            "elements": [{"name": "Save", "role": "Button", "x": 100, "y": 200, "width": 80, "height": 30, "value": ""}]
        }
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Save")
        assert result["found"] is True
        assert result["method"] == "uia"
        mock_ocr.assert_not_called()

    @mock.patch("tools.ocr.do_find_text")
    @mock.patch("tools.ui_automation.do_find_element")
    def test_uia_empty_falls_back_to_ocr(self, mock_uia, mock_ocr):
        mock_uia.return_value = {"found": False, "elements": []}
        mock_ocr.return_value = {
            "matches": [{"text": "Save", "x": 100, "y": 200, "width": 40, "height": 18}],
            "query": "Save",
            "total_words": 50,
        }
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Save")
        assert result["found"] is True
        assert result["method"] == "ocr"
        assert result["elements"][0]["x"] == 100

    @mock.patch("tools.ocr.do_find_text")
    @mock.patch("tools.ui_automation.do_find_element")
    def test_both_fail_returns_not_found(self, mock_uia, mock_ocr):
        mock_uia.return_value = {"found": False, "elements": []}
        mock_ocr.return_value = {"matches": [], "query": "Ghost", "total_words": 50}
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Ghost")
        assert result["found"] is False
        assert "method" not in result

    @mock.patch("tools.ocr.do_find_text")
    @mock.patch("tools.ui_automation.do_find_element")
    def test_uia_timeout_falls_back_to_ocr(self, mock_uia, mock_ocr):
        """If UIA raises any exception, fall through to OCR."""
        mock_uia.side_effect = Exception("UIA hung")
        mock_ocr.return_value = {
            "matches": [{"text": "Save", "x": 100, "y": 200, "width": 40, "height": 18}],
            "query": "Save",
            "total_words": 50,
        }
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Save")
        assert result["found"] is True
        assert result["method"] == "ocr"


class TestSmartFindOcrScoping:
    @mock.patch("tools.ui_automation.do_find_element", return_value={"found": False, "elements": []})
    @mock.patch("tools.ocr.do_find_text")
    def test_smart_find_passes_window_title_to_ocr(self, mock_find_text, mock_find_elem):
        """smart_find's OCR fallback should pass window_title through."""
        mock_find_text.return_value = {"matches": [
            {"text": "Hello", "x": 100, "y": 200, "width": 50, "height": 20}
        ]}
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Hello", window_title="Browser")
        mock_find_text.assert_called_once_with("Hello", window_title="Browser")

    @mock.patch("tools.ui_automation.do_find_element", return_value={"found": False, "elements": []})
    @mock.patch("tools.ocr.do_find_text")
    def test_smart_find_passes_none_window_title(self, mock_find_text, mock_find_elem):
        """smart_find without window_title passes None to OCR."""
        mock_find_text.return_value = {"matches": [], "query": "Ghost", "total_words": 0}
        from tools.ui_automation import do_smart_find
        do_smart_find("Ghost")
        mock_find_text.assert_called_once_with("Ghost", window_title=None)


class TestFindWindowUsesSharedMatching:
    @mock.patch("tools.ui_automation._get_desktop")
    def test_find_element_uses_shared_window_matching(self, mock_desktop):
        """_find_window should use find_matching_window from tools.windows."""
        mock_elem = mock.MagicMock()
        mock_elem.element_info.name = "Button"
        mock_elem.element_info.control_type = "Button"
        mock_elem.element_info.rectangle = mock.MagicMock(left=100, top=200, right=200, bottom=230)
        mock_elem.element_info.rich_text = ""

        mock_window = mock.MagicMock()
        mock_window.descendants.return_value = [mock_elem]
        mock_window.window_text.return_value = "Untitled - Notepad"

        mock_desktop.return_value.windows.return_value = [mock_window]

        from tools.ui_automation import do_find_element
        # "Notepad" is a substring of "Untitled - Notepad" so it matches via find_matching_window
        result = do_find_element(name="Button", window_title="Notepad")
        assert result["found"] is True


class TestRegister:
    def test_registers_five_tools(self):
        server = mock.MagicMock()
        from tools.ui_automation import register
        count = register(server)
        assert count == 6
