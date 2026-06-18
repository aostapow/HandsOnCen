"""Tests for template matching."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


class TestFindByTemplate:
    def test_missing_template(self):
        from tools.template_match import find_by_template
        result = find_by_template("/nonexistent/template.png")
        assert result["found"] is False

    def test_synthetic_match(self):
        cv2 = pytest.importorskip("cv2")
        import numpy as np
        from unittest import mock
        from tools.template_match import find_by_template

        screen = np.zeros((200, 300, 3), dtype=np.uint8)
        screen[50:80, 100:140] = (255, 0, 0)
        tmpl = screen[50:80, 100:140].copy()

        with tempfile.TemporaryDirectory() as tmp:
            tmpl_path = os.path.join(tmp, "btn.png")
            cv2.imwrite(tmpl_path, cv2.cvtColor(tmpl, cv2.COLOR_RGB2GRAY))
            with mock.patch("tools.screenshot.capture_screenshot", return_value={"path": "x"}):
                with mock.patch("tools.image_utils.load_image_from_screenshot", return_value=screen):
                    result = find_by_template(tmpl_path, threshold=0.9)
        assert result["found"] is True
        assert result["confidence"] >= 0.9
        assert result["element"]["width"] == 40
        assert result["element"]["height"] == 30
