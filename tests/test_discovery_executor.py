"""Tests for discovery probe executor."""

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


class TestDiscoveryExecutor:
    @mock.patch("detection.discovery.executor.observe_ui")
    @mock.patch("tools.screenshot.wait_for_change")
    @mock.patch("tools.input_tools.do_send_keys")
    @mock.patch("tools.highlight.clear_highlight")
    def test_dismiss_overlay_sends_escape(self, mock_clear, mock_keys, mock_wait, mock_obs):
        mock_wait.return_value = {"changed": True}
        mock_obs.return_value = {"fingerprint": "after"}
        from detection.discovery.executor import apply_probe
        with mock.patch("tools.ui_automation.do_ui_fingerprint", return_value={"hash": "before"}):
            result = apply_probe("dismiss_overlay")
        assert result["applied"] is True
        mock_keys.assert_called_with("{ESC}")
        mock_clear.assert_called_once()

    @mock.patch("detection.discovery.executor.observe_ui")
    @mock.patch("tools.screenshot.wait_for_change")
    @mock.patch("detection.backends.uia_backend.get_uia_backend")
    def test_expand_menu_calls_uia_expand(self, mock_get_backend, mock_wait, mock_obs):
        mock_wait.return_value = {"changed": False}
        mock_obs.return_value = {"fingerprint": "fp"}
        backend = mock.Mock()
        backend.expand_element.return_value = {"success": True}
        mock_get_backend.return_value = backend
        from detection.discovery.executor import apply_probe
        with mock.patch("tools.ui_automation.do_ui_fingerprint", return_value={"hash": "fp"}):
            result = apply_probe("expand_menu", target="Edit")
        assert result["applied"] is True
        backend.expand_element.assert_called_once()
