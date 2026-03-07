"""Win32 platform backend for HandsOn.

All functions raise NotImplementedError -- they will be filled in Task 2
when the existing Win32 code is extracted from the tools/ modules.
"""
from __future__ import annotations

__all__ = [
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


def get_dpi_scale() -> float:
    raise NotImplementedError("win32_backend: implement in Task 2")


def get_foreground_title() -> str:
    raise NotImplementedError("win32_backend: implement in Task 2")


def list_windows_native() -> list[dict]:
    raise NotImplementedError("win32_backend: implement in Task 2")


def focus_window_native(title: str, action: str) -> dict:
    raise NotImplementedError("win32_backend: implement in Task 2")


def classify_window_native(handle=None) -> dict:
    raise NotImplementedError("win32_backend: implement in Task 2")


def get_process_name_for_pid(pid: int) -> str:
    raise NotImplementedError("win32_backend: implement in Task 2")


def is_elevated(pid: int = None) -> bool:
    raise NotImplementedError("win32_backend: implement in Task 2")


def run_ocr_native(image_path: str) -> list[dict]:
    raise NotImplementedError("win32_backend: implement in Task 2")


def send_text_to_console(pid, text, hwnd=0) -> dict:
    raise NotImplementedError("win32_backend: implement in Task 2")


def send_keys_to_console(pid, keys, hwnd=0) -> dict:
    raise NotImplementedError("win32_backend: implement in Task 2")


def get_foreground_hwnd() -> int:
    raise NotImplementedError("win32_backend: implement in Task 2")


def get_class_name(hwnd) -> str:
    raise NotImplementedError("win32_backend: implement in Task 2")


def get_loaded_modules(pid) -> list[str]:
    raise NotImplementedError("win32_backend: implement in Task 2")


def find_host_terminal_hwnd() -> int | None:
    raise NotImplementedError("win32_backend: implement in Task 2")

