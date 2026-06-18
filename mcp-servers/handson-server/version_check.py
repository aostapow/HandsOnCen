"""Version detection and update notification for HandsOn."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

GITHUB_REPO = os.environ.get("HANDSON_GITHUB_REPO", "aostapow/HandsOnCen")
CHECK_INTERVAL_SECONDS = int(
    os.environ.get("HANDSON_VERSION_CHECK_INTERVAL", str(24 * 3600))
)
USER_AGENT = "HandsOn-MCP"
_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".handson", "version_check.json")
_VERSION_FILE = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "VERSION")
)
_VERSION_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+].*)?$")


@dataclass(frozen=True)
class VersionInfo:
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str
    source: str
    checked_at: str

    def format_status(self) -> str:
        if self.update_available:
            return (
                f"Update available: v{self.latest_version} "
                f"(running v{self.current_version}). {self.release_url}"
            )
        return f"Up to date (v{self.current_version}). {self.release_url}"


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a semver-ish version string into a comparable tuple."""
    match = _VERSION_RE.match(version.strip())
    if not match:
        raise ValueError(f"Invalid version: {version!r}")
    return tuple(int(part) for part in match.groups() if part is not None)


def is_newer_version(latest: str, current: str) -> bool:
    """Return True when *latest* is greater than *current*."""
    return parse_version(latest) > parse_version(current)


def get_local_version() -> str:
    """Read the installed version from the repo VERSION file."""
    with open(_VERSION_FILE, encoding="utf-8") as handle:
        return handle.read().strip()


def _github_request(path: str) -> object | None:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.load(response)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def _fetch_raw_version() -> Optional[str]:
    request = urllib.request.Request(
        f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/VERSION",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.read().decode("utf-8").strip()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def _best_tag_version(tags: list[dict]) -> Optional[str]:
    candidates: list[tuple[tuple[int, ...], str]] = []
    for tag in tags:
        name = str(tag.get("name", "")).strip()
        if not name:
            continue
        try:
            candidates.append((parse_version(name), name.lstrip("v")))
        except ValueError:
            continue
    if not candidates:
        return None
    return max(candidates)[1]


def fetch_latest_version() -> tuple[Optional[str], str, str]:
    """Return (latest_version, source, release_url)."""
    release_url = f"https://github.com/{GITHUB_REPO}/releases"

    release = _github_request(f"/repos/{GITHUB_REPO}/releases/latest")
    if isinstance(release, dict):
        tag_name = str(release.get("tag_name", "")).strip().lstrip("v")
        html_url = str(release.get("html_url", "")).strip()
        if tag_name:
            return tag_name, "release", html_url or release_url

    tags = _github_request(f"/repos/{GITHUB_REPO}/tags")
    if isinstance(tags, list):
        latest_tag = _best_tag_version(tags)
        if latest_tag:
            return latest_tag, "tag", f"{release_url}/tag/v{latest_tag}"

    remote_version = _fetch_raw_version()
    if remote_version:
        return remote_version, "version_file", release_url

    return None, "unavailable", release_url


def check_version(force: bool = False) -> VersionInfo:
    """Compare the local install against the latest version on GitHub."""
    current = get_local_version()
    checked_at = datetime.now(timezone.utc).isoformat()

    if not force:
        cached = _load_cache()
        if cached and cached.get("current_version") == current:
            checked_at_ts = _parse_checked_at(cached.get("checked_at", ""))
            if checked_at_ts is not None:
                age = datetime.now(timezone.utc).timestamp() - checked_at_ts
                if age < CHECK_INTERVAL_SECONDS and cached.get("latest_version"):
                    return VersionInfo(
                        current_version=current,
                        latest_version=str(cached["latest_version"]),
                        update_available=bool(cached.get("update_available")),
                        release_url=str(cached.get("release_url", "")),
                        source=str(cached.get("source", "cache")),
                        checked_at=str(cached.get("checked_at", checked_at)),
                    )

    latest, source, release_url = fetch_latest_version()
    if latest is None:
        info = VersionInfo(
            current_version=current,
            latest_version=current,
            update_available=False,
            release_url=release_url,
            source=source,
            checked_at=checked_at,
        )
        _save_cache(info)
        return info

    latest = latest.lstrip("v")
    info = VersionInfo(
        current_version=current,
        latest_version=latest,
        update_available=is_newer_version(latest, current),
        release_url=release_url,
        source=source,
        checked_at=checked_at,
    )
    _save_cache(info)
    return info


def maybe_notify_update() -> None:
    """Check for updates in the background and log a notice to stderr."""
    if os.environ.get("HANDSON_SKIP_VERSION_CHECK", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return

    def _run() -> None:
        try:
            info = check_version(force=False)
            if info.update_available:
                sys.stderr.write(f"[HandsOn] {info.format_status()}\n")
                sys.stderr.write(
                    "[HandsOn] Update with: git -C <repo> pull origin main\n"
                )
        except Exception:
            # Never block or crash MCP startup for version checks.
            return

    threading.Thread(target=_run, daemon=True, name="handson-version-check").start()


def _parse_checked_at(value: str) -> Optional[float]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _load_cache() -> Optional[dict]:
    try:
        with open(_CACHE_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _save_cache(info: VersionInfo) -> None:
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as handle:
        json.dump(asdict(info), handle, indent=2)
