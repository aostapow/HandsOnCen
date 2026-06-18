"""Tests for multi-backend detection orchestrator."""
from __future__ import annotations

import sys
from unittest import mock


class TestElementModel:
    def test_detected_element_center(self):
        from detection.element_model import DetectedElement
        e = DetectedElement(x=10, y=20, width=100, height=40)
        assert e.center() == (60, 40)

    def test_detected_element_clickable_point(self):
        from detection.element_model import DetectedElement
        e = DetectedElement(x=10, y=20, width=100, height=40, clickable_x=50, clickable_y=30)
        assert e.center() == (50, 30)

    def test_dict_to_legacy(self):
        from detection.element_model import dict_to_legacy_element
        d = dict_to_legacy_element({
            "name": "OK", "role": "Button", "x": 1, "y": 2,
            "width": 80, "height": 30, "automation_id": "btnOk",
        })
        assert d["automation_id"] == "btnOk"
        assert d["name"] == "OK"


class TestOrchestrator:
    def test_get_orchestrator_singleton(self):
        from detection.orchestrator import get_orchestrator
        a = get_orchestrator()
        b = get_orchestrator()
        assert a is b

    @mock.patch("detection.backends.uia_backend.UIABackend.find_elements")
    def test_find_elements_uia(self, mock_find):
        from detection.orchestrator import DetectionOrchestrator
        from detection.element_model import DetectedElement
        from detection.backends.uia_backend import UIABackend

        mock_find.return_value = [
            DetectedElement(name="File", role="MenuItem", x=0, y=0, width=50, height=25),
        ]
        backend = UIABackend()
        orch = DetectionOrchestrator()
        orch._backends = {"uia": backend}
        result = orch.find_elements(name="File", role="MenuItem")
        assert result["found"] is True
        assert result["elements"][0]["name"] == "File"

    def test_detection_health_structure(self):
        from detection.orchestrator import get_orchestrator
        orch = get_orchestrator()
        health = orch.detection_health()
        assert "backends" in health
        assert "framework" in health


class TestUIABackend:
    def test_is_available_windows(self):
        if sys.platform != "win32":
            return
        from detection.backends.uia_backend import UIABackend
        assert UIABackend().is_available() is True


class TestJABCheck:
    def test_check_java_bridge_no_java_home(self):
        if sys.platform != "win32":
            return
        from detection.backends.jab_backend import check_java_bridge
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("detection.backends.jab_backend._jab_available", return_value=False):
                result = check_java_bridge()
        assert result["available"] is False
        assert result.get("pyjab_installed") is False or any(
            "JAVA_HOME" in h or "pyjab" in h.lower()
            for h in result.get("hints", [])
        )


class TestWin32Backend:
    def test_get_foreground_hwnd(self):
        if sys.platform != "win32":
            return
        from handson_platform.win32_backend import get_foreground_hwnd
        hwnd = get_foreground_hwnd()
        assert isinstance(hwnd, int)

    def test_get_dpi_scale(self):
        if sys.platform != "win32":
            return
        from handson_platform.win32_backend import get_dpi_scale
        scale = get_dpi_scale()
        assert scale >= 0.5
