"""Tests for discovery probe planner."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


class TestDiscoveryPlanner:
    def test_plan_includes_verify_and_rescan(self):
        from detection.discovery.planner import plan_probes
        obs = {"framework": "winforms", "menu_bars": [{"name": "File"}], "tree_sample": []}
        planned = plan_probes(goal="Cancel", hints=["Cancel"], observation=obs)
        ids = [p["id"] for p in planned]
        assert "verify_context" in ids or "rescan" in ids
        assert "expand_menu" in ids

    def test_safe_mode_skips_dangerous_names(self):
        from detection.discovery.probes import is_safe_target
        assert is_safe_target("Save", safe_mode=True) is False
        assert is_safe_target("Cancel", safe_mode=True) is True

    def test_image_path_adds_template_probe(self):
        from detection.discovery.planner import plan_probes
        obs = {"framework": "winforms", "tree_sample": []}
        planned = plan_probes(
            goal="search",
            hints=["search"],
            observation=obs,
            image_path="/tmp/icon.png",
        )
        ids = [p["id"] for p in planned]
        assert "find_by_template" in ids
