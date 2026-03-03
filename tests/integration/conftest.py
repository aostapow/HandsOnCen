"""Shared fixtures for integration tests.

Creates/destroys a virtual desktop for each test session.
Saves failure screenshots to tests/integration/failures/.
"""

import os
import sys
import shutil
import tempfile
import pytest

_SERVER_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "mcp-servers", "handson-server"
)
sys.path.insert(0, _SERVER_DIR)

# Inject venv site-packages so deps like pywinauto are importable
if sys.platform == "win32":
    _VENV_SITE = os.path.join(_SERVER_DIR, ".venv", "Lib", "site-packages")
else:
    _py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    _VENV_SITE = os.path.join(_SERVER_DIR, ".venv", "lib", _py_ver, "site-packages")
if os.path.isdir(_VENV_SITE) and _VENV_SITE not in sys.path:
    sys.path.insert(0, _VENV_SITE)

# Ensure screenshot_manager is initialized (server.py normally does this)
from screenshot_manager import ScreenshotManager
from tools import screenshot as _screenshot_mod

if _screenshot_mod.screenshot_manager is None:
    _SCREENSHOT_DIR = os.path.join(tempfile.gettempdir(), "handson_screenshots")
    _screenshot_mod.screenshot_manager = ScreenshotManager(_SCREENSHOT_DIR)

FAILURE_DIR = os.path.join(os.path.dirname(__file__), "failures")


@pytest.fixture(scope="session", autouse=True)
def virtual_desktop():
    """Create an isolated virtual desktop for the test session."""
    from tools.desktop import do_virtual_desktop
    do_virtual_desktop("create")
    yield
    do_virtual_desktop("close")


@pytest.fixture(autouse=True)
def save_failure_screenshot(request):
    """Save a screenshot on test failure."""
    yield
    if request.node.rep_call and request.node.rep_call.failed:
        os.makedirs(FAILURE_DIR, exist_ok=True)
        from tools.screenshot import capture_screenshot
        shot = capture_screenshot()
        import base64
        path = os.path.join(FAILURE_DIR, f"{request.node.name}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(shot["image"]))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    import pluggy
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
