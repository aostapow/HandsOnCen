"""Integration tests for JAB backend (Windows + Java only)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


@pytest.mark.skipif(sys.platform != "win32", reason="JAB is Windows-only")
class TestJABIntegration:
    def test_check_java_bridge_runs(self):
        from detection.backends.jab_backend import check_java_bridge
        result = check_java_bridge()
        assert "available" in result
        assert "hints" in result
