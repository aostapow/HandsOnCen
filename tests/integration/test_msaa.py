"""Integration tests for MSAA backend (Windows only)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


@pytest.mark.skipif(sys.platform != "win32", reason="MSAA is Windows-only")
class TestMSAAIntegration:
    def test_msaa_backend_available(self):
        from detection.backends.msaa_backend import MSAABackend
        backend = MSAABackend()
        assert backend.is_available() is True

    def test_element_at_point_screen(self):
        from detection.backends.msaa_backend import MSAABackend
        backend = MSAABackend()
        # Should not crash at a point on screen (may or may not find element)
        elem = backend.element_at_point(100, 100)
        # Result can be None or an element — just verify no exception
        assert elem is None or elem.backend == "msaa"
