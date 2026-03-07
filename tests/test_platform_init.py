"""Tests for the handson_platform package scaffolding.

Verifies that:
- On macOS the darwin backend is auto-selected.
- All required function names are exported from the package.
"""

import os
import sys

import pytest

# Make the handson-server package importable
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)

# All functions the platform package must export
REQUIRED_NAMES = [
    "get_dpi_scale",
    "get_foreground_title",
    "list_windows_native",
    "focus_window_native",
    "classify_window_native",
    "get_process_name_for_pid",
    "is_elevated",
    "run_ocr_native",
    "send_text_to_console",
    "send_keys_to_console",
    "get_foreground_hwnd",
    "get_class_name",
    "get_loaded_modules",
    "find_host_terminal_hwnd",
]


class TestPlatformAutoSelect:
    """Verify the __init__.py auto-selection logic."""

    def test_darwin_backend_selected_on_macos(self):
        """On macOS (this machine), the darwin backend should be loaded."""
        assert sys.platform == "darwin", "This test must run on macOS"
        import handson_platform

        # The darwin_backend module should be the source of the exported names
        from handson_platform import darwin_backend

        for name in REQUIRED_NAMES:
            pkg_fn = getattr(handson_platform, name)
            backend_fn = getattr(darwin_backend, name)
            assert pkg_fn is backend_fn, (
                f"handson_platform.{name} should come from darwin_backend"
            )

    def test_unsupported_platform_raises(self):
        """Importing on an unsupported platform should raise RuntimeError."""
        import importlib
        from unittest import mock

        with mock.patch.object(sys, "platform", "freebsd"):
            # Force re-import to trigger __init__.py logic
            with pytest.raises(RuntimeError, match="does not support platform"):
                importlib.reload(
                    __import__("handson_platform")
                )

        # Restore the real module so other tests are unaffected
        importlib.reload(__import__("handson_platform"))


class TestExportedNames:
    """Verify every required function is accessible from the package."""

    @pytest.mark.parametrize("name", REQUIRED_NAMES)
    def test_function_exported(self, name):
        import handson_platform

        assert hasattr(handson_platform, name), (
            f"handson_platform is missing expected export: {name}"
        )
        assert callable(getattr(handson_platform, name)), (
            f"handson_platform.{name} should be callable"
        )


class TestDarwinImplementedFunctions:
    """Verify the functions that should actually work on macOS."""

    def test_get_dpi_scale_returns_float(self):
        from handson_platform import get_dpi_scale

        scale = get_dpi_scale()
        assert isinstance(scale, float)
        assert scale >= 1.0

    def test_is_elevated_returns_bool(self):
        from handson_platform import is_elevated

        result = is_elevated()
        assert isinstance(result, bool)
        # Normally tests don't run as root
        assert result is False

    def test_send_text_to_console_noop(self):
        from handson_platform import send_text_to_console

        result = send_text_to_console(pid=1, text="hello")
        assert result == {"success": True, "method": "pyautogui_passthrough"}

    def test_send_keys_to_console_noop(self):
        from handson_platform import send_keys_to_console

        result = send_keys_to_console(pid=1, keys="{ENTER}")
        assert result == {"success": True, "method": "pyautogui_passthrough"}

    def test_get_foreground_hwnd_returns_zero(self):
        from handson_platform import get_foreground_hwnd

        assert get_foreground_hwnd() == 0

    def test_get_class_name_returns_empty(self):
        from handson_platform import get_class_name

        assert get_class_name(0) == ""


class TestDarwinStubFunctions:
    """Verify that unimplemented functions raise NotImplementedError."""

    STUB_NAMES = [
        "get_loaded_modules",
    ]

    @pytest.mark.parametrize("name", STUB_NAMES)
    def test_stub_raises_not_implemented(self, name):
        import handson_platform

        fn = getattr(handson_platform, name)
        with pytest.raises(NotImplementedError, match="darwin_backend"):
            # Call with minimal dummy args
            if name == "get_loaded_modules":
                fn(pid=1)
            else:
                fn()

