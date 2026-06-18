"""Tests for image_utils and dual OCR."""

import os
import sys
from io import BytesIO
from unittest import mock

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))


class TestImageUtils:
    def test_load_image_pil_passthrough(self):
        from tools.image_utils import load_image
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        assert load_image(img) is img

    def test_region_to_element_dict(self):
        from tools.image_utils import region_to_element_dict
        d = region_to_element_dict({"x": 1, "y": 2, "w": 30, "h": 40, "text": "OK", "type": "text"})
        assert d["width"] == 30
        assert d["height"] == 40
        assert d["name"] == "OK"


class TestDualOcr:
    @mock.patch("tools.ocr._windows_ocr_on_image")
    @mock.patch("tools.ocr._rapid_ocr_on_image")
    def test_merge_dual(self, mock_rapid, mock_win):
        mock_rapid.return_value = [{"text": "Save", "x": 10, "y": 20, "width": 40, "height": 12}]
        mock_win.return_value = [{"text": "Save", "x": 11, "y": 21, "width": 38, "height": 12}]
        from tools.ocr import run_dual_ocr
        words = run_dual_ocr("fake.png")
        assert len(words) == 1
        assert words[0]["engine"] == "both"


class TestObjectRepository:
    def test_upsert_and_get(self, tmp_path, monkeypatch):
        from detection import object_repository as repo_mod
        monkeypatch.setattr(repo_mod, "_REPO_DIR", tmp_path)
        repo = repo_mod.load_repo("TestApp.exe")
        repo_mod.upsert_object(
            repo,
            "frmMain/btnSave",
            identification={"mandatory": {"automation_id": "btnSave"}},
            last_resolution={"backend": "uia", "layer": "native"},
        )
        obj = repo_mod.get_object(repo, "frmMain/btnSave")
        assert obj["identification"]["mandatory"]["automation_id"] == "btnSave"
