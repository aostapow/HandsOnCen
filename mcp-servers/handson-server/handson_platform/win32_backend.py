"""Win32 platform backend for HandsOn.

Native Windows APIs via ctypes — window enumeration, focus, DPI, process info.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
from typing import List, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32
shcore = ctypes.windll.shcore

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20

EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
)


def get_foreground_hwnd() -> int:
    return user32.GetForegroundWindow()


def get_foreground_title() -> str:
    hwnd = get_foreground_hwnd()
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_dpi_scale() -> float:
    """Return DPI scale for the monitor containing the foreground window."""
    try:
        hwnd = get_foreground_hwnd()
        monitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        if shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
            return dpi_x.value / 96.0
    except Exception:
        pass
    try:
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0


def get_process_name_for_pid(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = ctypes.wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            path = buf.value
            return path.rsplit("\\", 1)[-1] if "\\" in path else path
        return ""
    finally:
        kernel32.CloseHandle(handle)


def get_class_name(hwnd) -> str:
    if not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(int(hwnd), buf, 256)
    return buf.value


def is_elevated(pid: int = None) -> bool:
    if pid is None:
        pid = kernel32.GetCurrentProcessId()
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return True
    try:
        token = ctypes.wintypes.HANDLE()
        if not advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            return False
        try:
            elevation = ctypes.wintypes.DWORD()
            size = ctypes.wintypes.DWORD()
            advapi32.GetTokenInformation(
                token, TokenElevation, ctypes.byref(elevation),
                ctypes.sizeof(elevation), ctypes.byref(size),
            )
            return elevation.value != 0
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(handle)


def _enum_visible_windows() -> list[tuple[int, dict]]:
    """Return (hwnd, info_dict) for visible titled windows."""
    results: list[tuple[int, dict]] = []

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if not title:
            return True
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = get_process_name_for_pid(pid.value)
        results.append((hwnd, {
            "title": title,
            "process_name": proc_name,
            "x": rect.left,
            "y": rect.top,
            "width": rect.right - rect.left,
            "height": rect.bottom - rect.top,
            "hwnd": int(hwnd),
            "pid": pid.value,
        }))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return results


def list_windows_native() -> List[dict]:
    return [info for _, info in _enum_visible_windows()]


def focus_window_native(title: str, action: str) -> dict:
    from tools.windows import find_matching_window

    all_hwnds = _enum_visible_windows()
    match = find_matching_window(title, [info for _, info in all_hwnds])
    if match["window"] is None:
        return {"success": False, "error": f"No window matching '{title}' found"}

    matched_title = match["window"]["title"]
    target_hwnd = None
    for hwnd, info in all_hwnds:
        if info["title"] == matched_title:
            target_hwnd = hwnd
            break
    if target_hwnd is None:
        return {"success": False, "error": f"No window matching '{title}' found"}

    SW_MINIMIZE, SW_MAXIMIZE, SW_RESTORE, SW_SHOW = 6, 3, 9, 5

    if action == "focus":
        fg_hwnd = user32.GetForegroundWindow()
        fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
        our_tid = kernel32.GetCurrentThreadId()
        if fg_tid != our_tid:
            user32.AttachThreadInput(our_tid, fg_tid, True)
        user32.ShowWindow(target_hwnd, SW_RESTORE)
        user32.BringWindowToTop(target_hwnd)
        user32.SetForegroundWindow(target_hwnd)
        if fg_tid != our_tid:
            user32.AttachThreadInput(our_tid, fg_tid, False)
        import time
        for _ in range(50):
            time.sleep(0.01)
            if user32.GetForegroundWindow() == target_hwnd:
                break
    elif action == "minimize":
        user32.ShowWindow(target_hwnd, SW_MINIMIZE)
    elif action == "maximize":
        user32.ShowWindow(target_hwnd, SW_MAXIMIZE)
    elif action == "restore":
        user32.ShowWindow(target_hwnd, SW_RESTORE)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}

    return {"success": True, "window": matched_title, "action": action}


def classify_window_native(handle=None) -> dict:
    from tools.window_classify import classify_window
    hwnd = int(handle) if handle else get_foreground_hwnd()
    return classify_window(hwnd)


def get_loaded_modules(pid) -> list[str]:
    """Return basenames of DLLs loaded in a process."""
    import sys
    if sys.maxsize <= 2**32:
        LIST_MODULES_ALL = 0x03
    else:
        LIST_MODULES_ALL = 0x03

    psapi = ctypes.windll.psapi
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | 0x0400, False, pid)
    if not handle:
        return []
    try:
        needed = ctypes.wintypes.DWORD()
        psapi.EnumProcessModulesEx(handle, None, 0, ctypes.byref(needed), LIST_MODULES_ALL)
        count = needed.value // ctypes.sizeof(ctypes.c_void_p)
        if count == 0:
            return []
        arr = (ctypes.c_void_p * count)()
        psapi.EnumProcessModulesEx(
            handle, ctypes.byref(arr), ctypes.sizeof(arr),
            ctypes.byref(needed), LIST_MODULES_ALL,
        )
        modules = []
        buf = ctypes.create_unicode_buffer(260)
        for i in range(count):
            if psapi.GetModuleBaseNameW(handle, arr[i], buf, 260):
                modules.append(buf.value)
        return modules
    except Exception:
        return []
    finally:
        kernel32.CloseHandle(handle)


def run_ocr_native(image_path: str) -> list[dict]:
    raise NotImplementedError("win32_backend: use tools.ocr RapidOCR/Windows OCR")


def send_text_to_console(pid, text, hwnd=0) -> dict:
    raise NotImplementedError("win32_backend: use tools.input_tools console routing")


def send_keys_to_console(pid, keys, hwnd=0) -> dict:
    raise NotImplementedError("win32_backend: use tools.input_tools console routing")


def find_host_terminal_hwnd() -> int | None:
    for hwnd, info in _enum_visible_windows():
        proc = (info.get("process_name") or "").lower()
        if proc in ("windowsterminal.exe", "wt.exe", "powershell.exe", "cmd.exe"):
            return hwnd
    return None
