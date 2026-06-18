"""Tests for version detection and update notification."""

import json
import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)

import version_check


class TestParseVersion:
    def test_simple(self):
        assert version_check.parse_version("0.3.0") == (0, 3, 0)

    def test_with_v_prefix(self):
        assert version_check.parse_version("v1.2.3") == (1, 2, 3)

    def test_prerelease_suffix(self):
        assert version_check.parse_version("1.0.0-beta.1") == (1, 0, 0)

    def test_invalid(self):
        with pytest.raises(ValueError):
            version_check.parse_version("not-a-version")


class TestVersionCompare:
    def test_is_newer(self):
        assert version_check.is_newer_version("0.4.0", "0.3.0")
        assert version_check.is_newer_version("0.3.1", "0.3.0")
        assert not version_check.is_newer_version("0.3.0", "0.3.0")
        assert not version_check.is_newer_version("0.2.9", "0.3.0")


class TestGetLocalVersion:
    def test_reads_version_file(self):
        assert version_check.get_local_version() == "0.4.0"


class TestCheckVersion:
    def test_reports_update_when_remote_is_newer(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "version_check.json"
        monkeypatch.setattr(version_check, "_CACHE_FILE", str(cache_file))
        monkeypatch.setattr(
            version_check,
            "fetch_latest_version",
            lambda: ("0.5.0", "release", "https://github.com/aostapow/HandsOnCen/releases"),
        )

        info = version_check.check_version(force=True)

        assert info.current_version == "0.4.0"
        assert info.latest_version == "0.5.0"
        assert info.update_available is True
        assert info.source == "release"

    def test_uses_cache_when_fresh(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "version_check.json"
        monkeypatch.setattr(version_check, "_CACHE_FILE", str(cache_file))
        cache_file.write_text(
            json.dumps(
                {
                    "current_version": "0.4.0",
                    "latest_version": "0.5.0",
                    "update_available": True,
                    "release_url": "https://example.com",
                    "source": "release",
                    "checked_at": "2099-01-01T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )

        def fail_fetch():
            raise AssertionError("fetch_latest_version should not be called")

        monkeypatch.setattr(version_check, "fetch_latest_version", fail_fetch)
        info = version_check.check_version(force=False)

        assert info.latest_version == "0.5.0"
        assert info.update_available is True

    def test_best_tag_version(self):
        tags = [{"name": "v0.2.0"}, {"name": "0.3.0"}, {"name": "0.10.0"}]
        assert version_check._best_tag_version(tags) == "0.10.0"


class TestMaybeNotifyUpdate:
    def test_skips_when_disabled(self, monkeypatch):
        monkeypatch.setenv("HANDSON_SKIP_VERSION_CHECK", "1")
        with mock.patch.object(version_check, "check_version") as check:
            version_check.maybe_notify_update()
            check.assert_not_called()
