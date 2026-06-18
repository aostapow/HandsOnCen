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


def _mock_orch():
    return mock.patch("tools.ui_automation._orch")


class TestFindElement:
    @_mock_orch()
    def test_find_by_name(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.find_elements.return_value = {
            "found": True,
            "backend_used": "uia",
            "elements": [{
                "name": "File", "role": "MenuItem",
                "x": 10, "y": 20, "width": 100, "height": 30, "value": "",
            }],
        }

        from tools.ui_automation import do_find_element
        result = do_find_element(name="File", window_title="Notepad")

        assert result["found"] is True
        assert result["elements"][0]["name"] == "File"
        assert result["elements"][0]["role"] == "MenuItem"
        assert result["elements"][0]["x"] == 10
        assert result["elements"][0]["width"] == 100

    @_mock_orch()
    def test_find_no_match(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.find_elements.return_value = {"found": False, "elements": []}

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

        mock_click.assert_called_once_with(140, 215)

    @mock.patch("tools.ui_automation._fuzzy_find_nearest", return_value=None)
    @mock.patch("tools.ui_automation.do_find_element")
    def test_click_not_found(self, mock_find, mock_fuzzy):
        mock_find.return_value = {"found": False, "elements": []}

        from tools.ui_automation import do_click_element
        result = do_click_element(name="Ghost", window_title="Nowhere")

        assert result["success"] is False


class TestListElements:
    @_mock_orch()
    def test_list_returns_tree(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.list_elements.return_value = {
            "elements": [
                {"name": "File", "role": "MenuItem", "x": 0, "y": 0, "width": 50, "height": 25, "value": ""},
                {"name": "Edit", "role": "MenuItem", "x": 50, "y": 0, "width": 50, "height": 25, "value": ""},
            ],
            "count": 2,
            "backend_used": "uia",
        }

        from tools.ui_automation import do_list_elements
        result = do_list_elements(window_title="Notepad")

        assert len(result["elements"]) == 2
        assert result["elements"][0]["name"] == "File"
        assert result["elements"][1]["name"] == "Edit"


class TestListElementsRoleFilter:
    @_mock_orch()
    def test_role_filter_returns_only_matching_type(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.list_elements.return_value = {
            "elements": [
                {"name": "Amount", "role": "Spinner", "x": 100, "y": 200, "width": 100, "height": 30, "value": "42"},
            ],
            "count": 1,
            "backend_used": "uia",
        }

        from tools.ui_automation import do_list_elements
        result = do_list_elements(role="Spinner")

        assert len(result["elements"]) == 1
        assert result["elements"][0]["name"] == "Amount"
        mock_orch.list_elements.assert_called_once()
        assert mock_orch.list_elements.call_args.kwargs.get("role") == "Spinner"

    @_mock_orch()
    def test_no_role_uses_max_depth(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.list_elements.return_value = {"elements": [], "count": 0}

        from tools.ui_automation import do_list_elements
        do_list_elements(max_depth=5)

        assert mock_orch.list_elements.call_args.kwargs.get("max_depth") == 5


class TestGetFocusedElement:
    @mock.patch("pywinauto.Desktop")
    def test_returns_focused_element(self, mock_desktop_cls):
        mock_elem = mock.MagicMock()
        mock_elem.element_info.name = "Username"
        mock_elem.element_info.control_type = "Edit"
        mock_elem.element_info.rectangle = mock.MagicMock(
            left=100, top=200, right=300, bottom=230
        )
        mock_elem.element_info.rich_text = "admin"
        mock_elem.element_info.element = mock.MagicMock()
        mock_elem.element_info.automation_id = ""
        mock_elem.element_info.class_name = ""
        mock_elem.element_info.framework_id = ""
        mock_elem.element_info.process_id = 0
        mock_elem.element_info.handle = 0
        mock_elem.element_info.visible = True
        mock_elem.element_info.runtime_id = []
        mock_desktop_cls.return_value.get_focus.return_value = mock_elem

        from tools.ui_automation import do_get_focused_element
        result = do_get_focused_element()

        assert result["found"] is True
        assert result["element"]["name"] == "Username"
        assert result["element"]["role"] == "Edit"

    @mock.patch("pywinauto.Desktop")
    def test_returns_not_found_on_exception(self, mock_desktop_cls):
        mock_desktop_cls.return_value.get_focus.side_effect = Exception("UIA unavailable")

        from tools.ui_automation import do_get_focused_element
        result = do_get_focused_element()

        assert result["found"] is False


class TestSmartFind:
    @_mock_orch()
    def test_uia_found_returns_uia(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.smart_find.return_value = {
            "found": True,
            "method": "uia",
            "elements": [{"name": "Save", "role": "Button", "x": 100, "y": 200, "width": 80, "height": 30, "value": ""}],
        }
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Save")
        assert result["found"] is True
        assert result["method"] == "uia"

    @_mock_orch()
    def test_uia_empty_falls_back_to_ocr(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.smart_find.return_value = {
            "found": True,
            "method": "ocr",
            "elements": [{"name": "Save", "role": "text", "x": 100, "y": 200, "width": 40, "height": 18, "value": ""}],
        }
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Save")
        assert result["found"] is True
        assert result["method"] == "ocr"

    @_mock_orch()
    def test_both_fail_returns_not_found(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.smart_find.return_value = {"found": False, "elements": [], "error": "not found"}
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Ghost")
        assert result["found"] is False

    @_mock_orch()
    def test_uia_timeout_falls_back_to_ocr(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.smart_find.return_value = {
            "found": True,
            "method": "ocr",
            "elements": [{"name": "Save", "role": "text", "x": 100, "y": 200, "width": 40, "height": 18, "value": ""}],
        }
        from tools.ui_automation import do_smart_find
        result = do_smart_find("Save")
        assert result["found"] is True
        assert result["method"] == "ocr"


class TestSmartFindOcrScoping:
    @_mock_orch()
    def test_smart_find_passes_window_title_to_ocr(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.smart_find.return_value = {
            "found": True, "method": "ocr",
            "elements": [{"name": "Hello", "role": "text", "x": 100, "y": 200, "width": 50, "height": 20, "value": ""}],
        }
        from tools.ui_automation import do_smart_find
        do_smart_find("Hello", window_title="Browser")
        mock_orch.smart_find.assert_called_once_with(
            name="Hello", role=None, window_title="Browser", index=0,
            repo_path=None, agentic=False, remember=True, highlight=False,
        )

    @_mock_orch()
    def test_smart_find_passes_none_window_title(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.smart_find.return_value = {"found": False, "elements": [], "error": "x"}
        from tools.ui_automation import do_smart_find
        do_smart_find("Ghost")
        mock_orch.smart_find.assert_called_once_with(
            name="Ghost", role=None, window_title=None, index=0,
            repo_path=None, agentic=False, remember=True, highlight=False,
        )


class TestFindWindowUsesSharedMatching:
    @_mock_orch()
    def test_find_element_uses_orchestrator(self, mock_orch_fn):
        mock_orch = mock.MagicMock()
        mock_orch_fn.return_value = mock_orch
        mock_orch.find_elements.return_value = {
            "found": True,
            "backend_used": "uia",
            "elements": [{"name": "Button", "role": "Button", "x": 100, "y": 200, "width": 100, "height": 30, "value": ""}],
        }

        from tools.ui_automation import do_find_element
        result = do_find_element(name="Button", window_title="Notepad")
        assert result["found"] is True
        mock_orch.find_elements.assert_called_once()


class TestRegister:
    def test_registers_detection_tools(self):
        server = mock.MagicMock()
        from tools.ui_automation import register
        count = register(server)
        assert count == 20

    def test_registers_discovery_tools(self):
        server = mock.MagicMock()
        from tools.discovery import register
        count = register(server)
        assert count == 6

    def test_total_tool_count(self):
        server = mock.MagicMock()
        from tools import (
            screenshot, input_tools, windows, manage, uac, desktop,
            ui_automation, ocr, batch, framework_detect, target_window,
            visual_diff, watcher, version, discovery,
        )
        total = sum(
            fn(server)
            for fn in (
                screenshot.register, input_tools.register, windows.register,
                manage.register, uac.register, desktop.register,
                ui_automation.register, ocr.register, batch.register,
                framework_detect.register, target_window.register,
                visual_diff.register, watcher.register, version.register,
                discovery.register,
            )
        )
        assert total == 55
