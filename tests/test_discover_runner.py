"""Tests for discover_target runner."""

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


class TestDiscoverRunner:
    @mock.patch("detection.discovery.runner.resolve_target")
    @mock.patch("detection.discovery.runner.observe_ui")
    def test_discover_found_immediately(self, mock_obs, mock_resolve):
        mock_obs.return_value = {"framework": "winforms", "fingerprint": "abc"}
        mock_resolve.return_value = {
            "found": True,
            "elements": [{"name": "Cancel", "role": "Button", "x": 1, "y": 2, "width": 10, "height": 10}],
            "layer": "native",
        }
        from detection.discovery.runner import discover_target
        with mock.patch("detection.object_snapshot.capture_object_snapshot"):
            with mock.patch("tools.highlight.highlight_element_dict"):
                result = discover_target(hints=["Cancel"], max_steps=3)
        assert result["found"] is True
        assert result["element"]["name"] == "Cancel"

    @mock.patch("detection.discovery.runner.apply_probe")
    @mock.patch("detection.discovery.runner.plan_probes")
    @mock.patch("detection.discovery.runner.resolve_target")
    @mock.patch("detection.discovery.runner.observe_ui")
    def test_discover_two_iterations_then_found(self, mock_obs, mock_resolve, mock_plan, mock_apply):
        mock_obs.return_value = {"framework": "winforms", "fingerprint": "abc"}
        mock_resolve.side_effect = [
            {"found": False},
            {"found": True, "elements": [{"name": "Cancel", "role": "Button", "x": 1, "y": 2, "width": 10, "height": 10}], "layer": "native"},
        ]
        mock_plan.return_value = [{"id": "expand_menu", "target": "Edit", "reason": "menu", "risk": "low"}]
        mock_apply.return_value = {"applied": True, "ui_changed": True}
        from detection.discovery.runner import discover_target
        with mock.patch("detection.object_snapshot.capture_object_snapshot"):
            with mock.patch("tools.highlight.highlight_element_dict"):
                result = discover_target(hints=["Cancel"], max_steps=5)
        assert result["found"] is True
        assert mock_apply.call_count == 1
        assert any("expand_menu" in p for p in result.get("probes_tried", []))
