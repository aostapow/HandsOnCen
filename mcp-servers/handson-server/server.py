"""HandsOn MCP Server -- screen capture and interaction for Claude."""

from __future__ import annotations

import os
import sys
import subprocess
import site
import tempfile

# ---------------------------------------------------------------------------
# Venv bootstrap: ensure deps are available. Instead of re-exec (which can
# break stdio piping), we create the venv if needed and inject its
# site-packages directly into sys.path.
# ---------------------------------------------------------------------------
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))

# Place .venv outside the plugin cache to avoid locking/corrupting the
# cache directory.  Use ~/.handson/.venv as a stable, user-local location.
_HANDSON_DATA = os.path.join(os.path.expanduser("~"), ".handson")
_VENV_DIR = os.path.join(_HANDSON_DATA, ".venv")

if sys.platform == "win32":
    _VENV_SITE = os.path.join(_VENV_DIR, "Lib", "site-packages")
    _VENV_PIP = os.path.join(_VENV_DIR, "Scripts", "pip.exe")
else:
    _py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    _VENV_SITE = os.path.join(_VENV_DIR, "lib", _py_ver, "site-packages")
    _VENV_PIP = os.path.join(_VENV_DIR, "bin", "pip")

if not os.path.exists(_VENV_SITE):
    sys.stderr.write("[HandsOn] Creating virtual environment...\n")
    subprocess.check_call(
        [sys.executable, "-m", "venv", _VENV_DIR],
        stdout=subprocess.DEVNULL,
    )
    _req = os.path.join(_SERVER_DIR, "requirements.txt")
    sys.stderr.write("[HandsOn] Installing dependencies...\n")
    subprocess.check_call(
        [_VENV_PIP, "install", "-q", "-r", _req],
        stdout=subprocess.DEVNULL,
    )
    # Platform-specific dependencies
    if sys.platform == "darwin":
        sys.stderr.write("[HandsOn] Installing macOS dependencies (PyObjC)...\n")
        subprocess.check_call(
            [_VENV_PIP, "install", "-q",
             "pyobjc-core",
             "pyobjc-framework-Cocoa",
             "pyobjc-framework-Quartz",
             "pyobjc-framework-Vision",
             "pyobjc-framework-ApplicationServices"],
            stdout=subprocess.DEVNULL,
        )
    elif sys.platform == "win32":
        sys.stderr.write("[HandsOn] Installing Windows dependencies...\n")
        subprocess.check_call(
            [_VENV_PIP, "install", "-q", "pywinauto", "pyvda"],
            stdout=subprocess.DEVNULL,
        )
    sys.stderr.write("[HandsOn] Ready.\n")

# Inject venv site-packages so imports work without re-exec.
# Use site.addsitedir() to process .pth files (needed for pywin32 on Windows).
site.addsitedir(_VENV_SITE)
sys.path.insert(0, _VENV_SITE)
sys.path.insert(0, _SERVER_DIR)


# ---------------------------------------------------------------------------
# macOS permissions preflight -- request Accessibility + Screen Recording
# upfront so the user sees all permission dialogs at startup, not mid-task.
# ---------------------------------------------------------------------------
def _macos_preflight_permissions():
    """Check and request macOS permissions. Logs status to stderr."""
    missing = []

    # 1. Accessibility (needed for pyautogui input + AXUIElement)
    try:
        from ApplicationServices import (  # type: ignore[import-untyped]
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        trusted = AXIsProcessTrustedWithOptions(
            {kAXTrustedCheckOptionPrompt: True}
        )
        if not trusted:
            missing.append("Accessibility")
    except Exception:
        # AXIsProcessTrustedWithOptions prompt option can fail on some
        # PyObjC versions; fall back to non-prompting check.
        try:
            from ApplicationServices import AXIsProcessTrusted  # type: ignore[import-untyped]
            if not AXIsProcessTrusted():
                missing.append("Accessibility")
                subprocess.Popen(
                    ["open", "x-apple.systempreferences:"
                     "com.apple.preference.security?Privacy_Accessibility"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    # 2. Screen Recording (needed for screenshots + window titles)
    try:
        from Quartz import (  # type: ignore[import-untyped]
            CGPreflightScreenCaptureAccess,
            CGRequestScreenCaptureAccess,
        )
        if not CGPreflightScreenCaptureAccess():
            CGRequestScreenCaptureAccess()  # triggers dialog on first call
            missing.append("Screen Recording")
    except ImportError:
        # macOS < 11 or Quartz not available; skip check
        pass

    if missing:
        perms = " and ".join(missing)
        sys.stderr.write(
            f"[HandsOn] macOS permissions needed: {perms}\n"
            f"[HandsOn] Grant access in System Settings > Privacy & Security,\n"
            f"[HandsOn] then restart the server for changes to take effect.\n"
        )
    else:
        sys.stderr.write("[HandsOn] macOS permissions OK.\n")


if sys.platform == "darwin":
    _macos_preflight_permissions()


# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------
from mcp.server.fastmcp import FastMCP
from screenshot_manager import ScreenshotManager

SCREENSHOT_DIR = os.path.join(tempfile.gettempdir(), "handson_screenshots")
screenshot_mgr = ScreenshotManager(SCREENSHOT_DIR)

mcp = FastMCP("handson")

# Register all tool modules
from tools import screenshot, input_tools, windows, manage, uac, desktop, ui_automation, ocr, batch, framework_detect, target_window, visual_diff, watcher

# Set screenshot_manager reference for tools that need it
screenshot.screenshot_manager = screenshot_mgr

screenshot.register(mcp)
input_tools.register(mcp)
windows.register(mcp)
manage.register(mcp)
uac.register(mcp)
desktop.register(mcp)
ui_automation.register(mcp)
ocr.register(mcp)
batch.register(mcp)
framework_detect.register(mcp)
target_window.register(mcp)
visual_diff.register(mcp)
watcher.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
