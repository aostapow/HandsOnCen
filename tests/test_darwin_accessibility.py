"""macOS accessibility tests using AXUIElement."""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestRoleMapping:
    """Test Windows <-> macOS role name conversion."""

    def test_windows_to_ax_known(self):
        from handson_platform.darwin_backend import windows_role_to_ax

        assert windows_role_to_ax("Button") == "AXButton"
        assert windows_role_to_ax("Edit") == "AXTextField"
        assert windows_role_to_ax("CheckBox") == "AXCheckBox"
        assert windows_role_to_ax("Window") == "AXWindow"
        assert windows_role_to_ax("Slider") == "AXSlider"

    def test_windows_to_ax_unknown(self):
        from handson_platform.darwin_backend import windows_role_to_ax

        assert windows_role_to_ax("CustomWidget") == "AXCustomWidget"

    def test_ax_to_windows_known(self):
        from handson_platform.darwin_backend import ax_role_to_windows

        assert ax_role_to_windows("AXButton") == "Button"
        assert ax_role_to_windows("AXTextField") == "Edit"
        assert ax_role_to_windows("AXTextArea") == "Edit"
        assert ax_role_to_windows("AXCheckBox") == "CheckBox"

    def test_ax_to_windows_unknown_strips_prefix(self):
        from handson_platform.darwin_backend import ax_role_to_windows

        assert ax_role_to_windows("AXUnknownThing") == "UnknownThing"

    def test_ax_to_windows_no_prefix(self):
        from handson_platform.darwin_backend import ax_role_to_windows

        assert ax_role_to_windows("SomethingElse") == "SomethingElse"


class TestAxElementToDict:
    """Test ax_element_to_dict with mocked AXUIElement."""

    def test_converts_element_with_all_attrs(self):
        from handson_platform.darwin_backend import ax_element_to_dict

        mock_elem = mock.MagicMock()
        mock_pos = mock.MagicMock()
        mock_pos.x = 100
        mock_pos.y = 200
        mock_size = mock.MagicMock()
        mock_size.width = 80
        mock_size.height = 30

        mock_copy = mock.MagicMock()

        def fake_copy(elem, attr, _):
            values = {
                "AXRole": (0, "AXButton"),
                "AXTitle": (0, "OK"),
                "AXValue": (0, ""),
                "AXPosition": (0, mock_pos),
                "AXSize": (0, mock_size),
            }
            return values.get(attr, (-1, None))

        mock_copy.side_effect = fake_copy

        # Mock the ApplicationServices module so the import inside the function works
        with mock.patch.dict("sys.modules", {
            "ApplicationServices": mock.MagicMock(
                AXUIElementCopyAttributeValue=mock_copy
            ),
        }):
            result = ax_element_to_dict(mock_elem)

        assert result is not None
        assert result["name"] == "OK"
        assert result["role"] == "Button"
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["width"] == 80
        assert result["height"] == 30

    def test_returns_element_without_position(self):
        """Elements without position should still return with zeroed coords."""
        from handson_platform.darwin_backend import ax_element_to_dict

        mock_elem = mock.MagicMock()
        with mock.patch.dict("sys.modules", {
            "ApplicationServices": mock.MagicMock(
                AXUIElementCopyAttributeValue=mock.MagicMock(
                    side_effect=lambda e, a, n: {
                        "AXRole": (0, "AXStaticText"),
                        "AXTitle": (0, "Hello"),
                        "AXValue": (-1, None),
                        "AXPosition": (-1, None),
                        "AXSize": (-1, None),
                    }.get(a, (-1, None))
                )
            ),
        }):
            result = ax_element_to_dict(mock_elem)

        assert result is not None
        assert result["name"] == "Hello"
        assert result["role"] == "Text"
        assert result["x"] == 0
        assert result["y"] == 0


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
class TestDarwinUiAutomationRouting:
    """Test that ui_automation.py routes to macOS functions on darwin."""

    def test_do_find_element_calls_darwin_path(self):
        from tools.ui_automation import do_find_element

        with mock.patch("tools.ui_automation._do_find_element_darwin") as mock_darwin:
            mock_darwin.return_value = {"found": False, "elements": []}
            result = do_find_element(name="test")
            mock_darwin.assert_called_once()

    def test_do_list_elements_calls_darwin_path(self):
        from tools.ui_automation import do_list_elements

        with mock.patch("tools.ui_automation._do_list_elements_darwin") as mock_darwin:
            mock_darwin.return_value = {"elements": [], "count": 0}
            result = do_list_elements()
            mock_darwin.assert_called_once()

    def test_do_get_focused_element_calls_darwin_path(self):
        from tools.ui_automation import do_get_focused_element

        with mock.patch("handson_platform.darwin_backend.ax_get_focused_element") as mock_ax:
            mock_ax.return_value = {"found": False, "error": "test"}
            result = do_get_focused_element()
            mock_ax.assert_called_once()
