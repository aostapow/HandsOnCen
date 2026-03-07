"""Input tools -- click, type, send keys, scroll, drag, hover.

Provides core input functions backed by PyAutoGUI with smart routing
to Win32 console APIs for console windows. Registers MCP tools on a
Server instance.
"""

import sys
from typing import List, Optional

import pyautogui

from tools.window_classify import get_foreground_type, classify_window

pyautogui.FAILSAFE = False  # disabled — virtual desktop isolation is the safety net
pyautogui.PAUSE = 0.05      # tightened — we have our own safety layer

# Win32-only: ctypes for console API (WriteConsoleInputW, AttachConsole, etc.)
# ctypes.wintypes may not be available on all non-Windows platforms, and
# ctypes.windll only exists on Windows.
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes
    _HAS_WIN32 = True
else:
    _HAS_WIN32 = False

# Virtual key code mapping for special keys
_VK_MAP = {
    "enter": 0x0D, "return": 0x0D,
    "tab": 0x09,
    "escape": 0x1B, "esc": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}

STD_INPUT_HANDLE = -10
KEY_EVENT = 0x0001
WM_CHAR = 0x0102


if _HAS_WIN32:
    def _make_key_event(char_or_vk: int, is_char: bool = True, key_down: bool = True):
        """Create a KEY_EVENT_RECORD for WriteConsoleInputW."""

        class KEY_EVENT_RECORD(ctypes.Structure):
            _fields_ = [
                ("bKeyDown", ctypes.wintypes.BOOL),
                ("wRepeatCount", ctypes.wintypes.WORD),
                ("wVirtualKeyCode", ctypes.wintypes.WORD),
                ("wVirtualScanCode", ctypes.wintypes.WORD),
                ("UnicodeChar", ctypes.c_wchar),
                ("dwControlKeyState", ctypes.wintypes.DWORD),
            ]

        class INPUT_RECORD(ctypes.Structure):
            class _Event(ctypes.Union):
                _fields_ = [("KeyEvent", KEY_EVENT_RECORD)]
            _fields_ = [
                ("EventType", ctypes.wintypes.WORD),
                ("Event", _Event),
            ]

        rec = INPUT_RECORD()
        rec.EventType = KEY_EVENT
        rec.Event.KeyEvent.bKeyDown = key_down
        rec.Event.KeyEvent.wRepeatCount = 1
        if is_char:
            rec.Event.KeyEvent.UnicodeChar = chr(char_or_vk)
            rec.Event.KeyEvent.wVirtualKeyCode = 0
        else:
            rec.Event.KeyEvent.wVirtualKeyCode = char_or_vk
            rec.Event.KeyEvent.UnicodeChar = '\0'
        rec.Event.KeyEvent.wVirtualScanCode = 0
        rec.Event.KeyEvent.dwControlKeyState = 0
        return rec


def _send_text_to_console(pid: int, text: str, hwnd: int = 0) -> dict:
    """Send text to a console process via WriteConsoleInputW.

    Falls back to SendMessage(WM_CHAR) if AttachConsole fails (e.g., elevated console).
    """
    if not _HAS_WIN32:
        return {"success": False, "error": "Windows only"}

    # Try AttachConsole first
    ctypes.windll.kernel32.FreeConsole()
    if ctypes.windll.kernel32.AttachConsole(pid):
        try:
            handle = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
            written = ctypes.wintypes.DWORD()
            for ch in text:
                # Key down
                rec_down = _make_key_event(ord(ch), is_char=True, key_down=True)
                ctypes.windll.kernel32.WriteConsoleInputW(
                    handle, ctypes.byref(rec_down), 1, ctypes.byref(written)
                )
                # Key up
                rec_up = _make_key_event(ord(ch), is_char=True, key_down=False)
                ctypes.windll.kernel32.WriteConsoleInputW(
                    handle, ctypes.byref(rec_up), 1, ctypes.byref(written)
                )
            return {"success": True, "method": "WriteConsoleInput", "chars": len(text)}
        finally:
            ctypes.windll.kernel32.FreeConsole()
    else:
        # Fallback: SendMessage WM_CHAR (works cross-elevation)
        if not hwnd:
            return {"success": False, "error": "AttachConsole failed and no hwnd for SendMessage"}
        for ch in text:
            ctypes.windll.user32.SendMessageW(hwnd, WM_CHAR, ord(ch), 0)
        return {"success": True, "method": "SendMessage", "chars": len(text)}


def _send_keys_to_console(pid: int, keys: str, hwnd: int = 0) -> dict:
    """Send special keys (enter, tab, arrows, etc.) to a console process."""
    if not _HAS_WIN32:
        return {"success": False, "error": "Windows only"}

    parts = parse_hotkey(keys)

    ctypes.windll.kernel32.FreeConsole()
    if ctypes.windll.kernel32.AttachConsole(pid):
        try:
            handle = ctypes.windll.kernel32.GetStdHandle(STD_INPUT_HANDLE)
            written = ctypes.wintypes.DWORD()
            for key in parts:
                vk = _VK_MAP.get(key)
                if vk:
                    rec_down = _make_key_event(vk, is_char=False, key_down=True)
                    ctypes.windll.kernel32.WriteConsoleInputW(
                        handle, ctypes.byref(rec_down), 1, ctypes.byref(written)
                    )
                    rec_up = _make_key_event(vk, is_char=False, key_down=False)
                    ctypes.windll.kernel32.WriteConsoleInputW(
                        handle, ctypes.byref(rec_up), 1, ctypes.byref(written)
                    )
                else:
                    # Unknown key — try as single char
                    if len(key) == 1:
                        rec = _make_key_event(ord(key), is_char=True, key_down=True)
                        ctypes.windll.kernel32.WriteConsoleInputW(
                            handle, ctypes.byref(rec), 1, ctypes.byref(written)
                        )
            return {"success": True, "method": "WriteConsoleInput"}
        finally:
            ctypes.windll.kernel32.FreeConsole()
    else:
        return {"success": False, "error": "AttachConsole failed"}


# ------------------------------------------------------------------
# Helper / validation functions
# ------------------------------------------------------------------

def parse_hotkey(keys: str) -> List[str]:
    """Parse a hotkey string like ``'ctrl+s'`` into ``['ctrl', 's']``."""
    return [k.strip().lower() for k in keys.split("+")]


# macOS AppleScript keycodes for special keys
_APPLESCRIPT_KEYCODES = {
    "enter": 36, "return": 36, "tab": 48, "space": 49,
    "escape": 53, "esc": 53, "delete": 51, "backspace": 51,
    "up": 126, "down": 125, "left": 123, "right": 124,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96,
    "f6": 97, "f7": 98, "f8": 100, "f9": 101, "f10": 109,
    "f11": 103, "f12": 111,
}

# Modifier name mapping to AppleScript "using" syntax
_APPLESCRIPT_MODIFIERS = {
    "command": "command down", "cmd": "command down",
    "control": "control down", "ctrl": "control down",
    "option": "option down", "alt": "option down",
    "shift": "shift down",
}


def _send_keys_applescript(keys: str) -> Optional[dict]:
    """Send keys via AppleScript System Events. Returns result dict or None to fall through.

    More reliable than pyautogui.hotkey() on macOS because it uses the
    accessibility system rather than raw CGEvents.
    """
    import subprocess as _sp
    parts = parse_hotkey(keys)

    # Separate modifiers from the actual key
    modifiers = []
    key_part = None
    for p in parts:
        if p in _APPLESCRIPT_MODIFIERS:
            modifiers.append(_APPLESCRIPT_MODIFIERS[p])
        else:
            key_part = p

    if key_part is None:
        return None  # All modifiers, no key — fall through

    # Build the AppleScript command
    using_clause = ""
    if modifiers:
        using_clause = f" using {{{', '.join(modifiers)}}}"

    if key_part in _APPLESCRIPT_KEYCODES:
        # Special key — use "key code"
        script = (
            f'tell application "System Events" to key code '
            f'{_APPLESCRIPT_KEYCODES[key_part]}{using_clause}'
        )
    elif len(key_part) == 1:
        # Single character — use "keystroke"
        script = (
            f'tell application "System Events" to keystroke '
            f'"{key_part}"{using_clause}'
        )
    else:
        return None  # Unknown key — fall through to pyautogui

    try:
        _sp.run(["osascript", "-e", script], capture_output=True, timeout=2)
    except Exception:
        return None  # Fall through to pyautogui on failure
    return {"action": "send_keys", "keys": keys, "method": "applescript"}


def validate_button(button: str) -> str:
    """Validate and normalise a mouse button name.

    Raises :class:`ValueError` if *button* is not one of
    ``left``, ``right``, ``middle``.
    """
    valid = ("left", "right", "middle")
    if button.lower() not in valid:
        raise ValueError(
            f"Invalid button '{button}'. Must be one of: {valid}"
        )
    return button.lower()


def validate_direction(direction: str) -> str:
    """Validate and normalise a scroll direction.

    Raises :class:`ValueError` if *direction* is not one of
    ``up``, ``down``, ``left``, ``right``.
    """
    valid = ("up", "down", "left", "right")
    if direction.lower() not in valid:
        raise ValueError(
            f"Invalid direction '{direction}'. Must be one of: {valid}"
        )
    return direction.lower()


# ------------------------------------------------------------------
# Core functions
# ------------------------------------------------------------------

def do_click(x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
    """Click at (*x*, *y*) with the given *button* and *clicks* count.

    After clicking, checks if the foreground window title changed and
    captures a small region around the click point to detect visual changes.
    """
    import time
    from tools.target_window import ensure_focus
    from tools.screenshot import capture_screenshot, compare_screenshots
    ensure_focus()
    button = validate_button(button)

    # Capture title before click for navigation detection
    from tools.windows import get_foreground_title
    pre_title = get_foreground_title()

    # Capture 400x400 region around click point before click
    half = 200
    region = {
        "x": max(0, x - half),
        "y": max(0, y - half),
        "w": 400,
        "h": 400,
    }
    before = capture_screenshot(region=region)

    pyautogui.click(x=x, y=y, button=button, clicks=clicks)

    time.sleep(0.5)

    # Re-focus target so we compare target app title, not terminal
    ensure_focus()

    # Check if foreground window changed
    post_title = get_foreground_title()

    # Capture same region after click
    after = capture_screenshot(region=region)
    pixel_diff = compare_screenshots(before["image"], after["image"])

    result = {
        "action": "click",
        "x": x,
        "y": y,
        "button": button,
        "clicks": clicks,
        "visual_change": pixel_diff >= 0.005,
        "pixel_diff": pixel_diff,
    }

    if pre_title and post_title and pre_title != post_title:
        result["navigation_warning"] = (
            f"Window title changed: '{pre_title[:80]}' -> '{post_title[:80]}'. "
            "If this was unintended, use alt+left to go back."
        )

    return result


def do_type_text(text: str, interval: float = 0.02) -> dict:
    """Type text — routes to Win32 console API for console windows, pyautogui otherwise."""
    from tools.target_window import ensure_focus
    ensure_focus()
    fg = get_foreground_type()
    if fg["type"] == "console":
        result = _send_text_to_console(fg["pid"], text, hwnd=fg["hwnd"])
        return {"action": "type_text", "text": text, "interval": interval, "method": result.get("method", "console")}
    pyautogui.write(text, interval=interval)
    return {"action": "type_text", "text": text, "interval": interval, "method": "pyautogui"}


def do_send_keys(keys: str) -> dict:
    """Send keys — routes to Win32 console API for console windows, pyautogui otherwise."""
    from tools.target_window import ensure_focus
    ensure_focus()
    fg = get_foreground_type()
    if fg["type"] == "console" and _HAS_WIN32:
        parts = parse_hotkey(keys)
        # For single non-modifier keys, use console API
        if len(parts) == 1 and parts[0] in _VK_MAP:
            _send_keys_to_console(fg["pid"], keys, hwnd=fg["hwnd"])
            return {"action": "send_keys", "keys": keys, "method": "console"}
    # macOS: use AppleScript for key combos — pyautogui.hotkey() is unreliable
    # with modifier keys on macOS (sends raw CGEvents that get misinterpreted).
    if sys.platform == "darwin":
        result = _send_keys_applescript(keys)
        if result is not None:
            return result
    # Fall through to pyautogui for single keys or non-macOS
    parts = parse_hotkey(keys)
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)
    return {"action": "send_keys", "keys": keys, "method": "pyautogui"}


def do_scroll(
    x: int, y: int, direction: str,
    amount: Optional[int] = None,
    pages: Optional[float] = None,
) -> dict:
    """Move to (*x*, *y*) and scroll in *direction*.

    Specify *pages* (e.g. 1 = one full page, 0.5 = half page) for
    keyboard-based scrolling via PageDown/PageUp, which is DPI-independent
    and always scrolls exactly one page per press.

    Specify *amount* for raw mouse-wheel clicks.

    Defaults to ``pages=1`` (one full page) if neither is given.

    Captures before/after screenshots and compares to detect whether the
    scroll actually changed anything on screen.
    """
    import time
    from tools.target_window import ensure_focus
    from tools.screenshot import capture_screenshot, compare_screenshots
    ensure_focus()
    direction = validate_direction(direction)

    pyautogui.moveTo(x, y)

    # Capture before scroll
    before = capture_screenshot()

    use_keyboard = False
    if amount is not None:
        # Explicit wheel clicks requested — use mouse wheel
        if direction == "up":
            pyautogui.scroll(amount)
        elif direction == "down":
            pyautogui.scroll(-amount)
        elif direction == "left":
            pyautogui.hscroll(-amount)
        elif direction == "right":
            pyautogui.hscroll(amount)
    elif direction in ("left", "right"):
        # Horizontal scroll — no keyboard equivalent, use wheel
        wheel_amount = 50 if pages is None else max(1, int(50 * (pages or 1)))
        if direction == "left":
            pyautogui.hscroll(-wheel_amount)
        else:
            pyautogui.hscroll(wheel_amount)
    else:
        # Vertical page-based scroll — use PageDown/PageUp (DPI-independent)
        use_keyboard = True
        if pages is None:
            pages = 1.0
        key = "pagedown" if direction == "down" else "pageup"
        full_pages = int(pages)
        remainder = pages - full_pages
        # Press PageDown/PageUp for each full page
        for _ in range(full_pages):
            pyautogui.press(key)
            time.sleep(0.05)
        # For fractional pages (e.g. 0.5), use arrow key presses as approximation
        if remainder > 0:
            arrow = "down" if direction == "down" else "up"
            # ~30 arrow presses ≈ 1 page, scale by remainder
            arrow_presses = max(1, int(30 * remainder))
            for _ in range(arrow_presses):
                pyautogui.press(arrow)

    time.sleep(0.3)

    # Capture after scroll
    after = capture_screenshot()
    pixel_diff = compare_screenshots(before["image"], after["image"])

    result = {
        "action": "scroll",
        "x": x,
        "y": y,
        "direction": direction,
        "scroll_detected": pixel_diff >= 0.005,
        "pixel_diff": pixel_diff,
    }
    if use_keyboard:
        result["method"] = "keyboard"
        result["pages"] = pages
    else:
        result["method"] = "wheel"
        result["amount"] = amount

    if pixel_diff < 0.005:
        result["scroll_warning"] = (
            "No visual change detected after scroll. "
            "You may have hit the scroll boundary, or the wrong element received the scroll."
        )

    return result


def do_drag(
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    duration: float = 0.5,
) -> dict:
    """Drag from (*from_x*, *from_y*) to (*to_x*, *to_y*)."""
    from tools.target_window import ensure_focus
    ensure_focus()
    pyautogui.moveTo(from_x, from_y)
    dx = to_x - from_x
    dy = to_y - from_y
    pyautogui.drag(dx, dy, duration=duration)
    return {
        "action": "drag",
        "from_x": from_x,
        "from_y": from_y,
        "to_x": to_x,
        "to_y": to_y,
        "duration": duration,
    }


def do_hover(x: int, y: int) -> dict:
    """Move the mouse to (*x*, *y*) without clicking."""
    from tools.target_window import ensure_focus
    ensure_focus()
    pyautogui.moveTo(x, y)
    return {
        "action": "hover",
        "x": x,
        "y": y,
    }


def do_get_mouse_position() -> dict:
    """Return the current mouse cursor coordinates."""
    x, y = pyautogui.position()
    return {"x": x, "y": y}


# ------------------------------------------------------------------
# MCP tool registration
# ------------------------------------------------------------------

def register(server) -> int:
    """Register the seven input MCP tools on *server*.

    Returns the number of tools registered (7).
    """
    import base64 as _b64
    from mcp.server.fastmcp import Image as McpImage
    from tools.safety import with_timeout, ActionTimeoutError

    @server.tool()
    def click(
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
    ) -> list:
        """Click at a screen position. Returns a screenshot after clicking.

        Parameters:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            button: Mouse button — "left", "right", or "middle".
            clicks: Number of clicks (1 = single, 2 = double).
        """
        try:
            result = with_timeout(
                lambda: do_click(x, y, button=button, clicks=clicks),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 5s clicking at ({x}, {y}). The UI may be frozen."

        from tools.screenshot import capture_screenshot
        shot = capture_screenshot()
        diff_pct = result.get('pixel_diff', 0) * 100

        msg = f"Clicked ({result['button']}) at ({result['x']}, {result['y']}) x{result['clicks']}. Screenshot: {shot['width']}x{shot['height']}"
        if result.get("navigation_warning"):
            msg += f"\n\u26a0\ufe0f {result['navigation_warning']}"
        if result.get("visual_change"):
            msg += f"\nVisual change detected ({diff_pct:.1f}% diff)"
        else:
            msg += "\nNo visual change detected"

        return [
            McpImage(data=_b64.b64decode(shot["image"]), format="png"),
            msg,
        ]

    @server.tool()
    def type_text(
        text: str,
        interval: float = 0.02,
    ) -> str:
        """Type text character by character. For key combos use send_keys instead.

        Parameters:
            text: The string to type.
            interval: Seconds between each keystroke (default 0.02).
        """
        try:
            result = with_timeout(
                lambda: do_type_text(text, interval=interval),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 10s typing text. The UI may be frozen."
        return f"Typed {len(result['text'])} characters."

    @server.tool()
    def send_keys(keys: str) -> str:
        """Send a key or key-combination (e.g. 'enter', 'ctrl+s', 'ctrl+shift+p').

        Parameters:
            keys: Key name or combo joined with '+'.
        """
        try:
            result = with_timeout(
                lambda: do_send_keys(keys),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 5s sending keys '{keys}'. The UI may be frozen."
        return f"Sent keys: {result['keys']}"

    @server.tool()
    def scroll(
        x: int,
        y: int,
        direction: str,
        amount: Optional[int] = None,
        pages: Optional[float] = None,
    ) -> list:
        """Scroll the mouse wheel at a screen position.

        Parameters:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            direction: One of "up", "down", "left", "right".
            amount: Number of scroll clicks (default 50). Overrides amount.
            pages: Scroll by pages instead (1 = full page, 0.5 = half). Overrides amount.
        """
        try:
            result = with_timeout(
                lambda: do_scroll(x, y, direction, amount=amount, pages=pages),
                timeout=10.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 10s scrolling at ({x}, {y}). The UI may be frozen."

        from tools.screenshot import capture_screenshot
        shot = capture_screenshot()
        diff_pct = result['pixel_diff'] * 100

        method = result.get("method", "wheel")
        if method == "keyboard":
            msg = f"Scrolled {result['direction']} {result['pages']} page(s) via PageDown/PageUp at ({result['x']}, {result['y']}). Pixel diff: {diff_pct:.1f}%"
        else:
            msg = f"Scrolled {result['direction']} by {result.get('amount', '?')} at ({result['x']}, {result['y']}). Pixel diff: {diff_pct:.1f}%"
        if result.get("scroll_warning"):
            msg += f"\n\u26a0\ufe0f {result['scroll_warning']}"

        return [
            McpImage(data=_b64.b64decode(shot["image"]), format="png"),
            msg,
        ]

    @server.tool()
    def drag(
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
    ) -> list:
        """Drag from one position to another. Returns a screenshot after dragging.

        Parameters:
            from_x: Start X coordinate.
            from_y: Start Y coordinate.
            to_x: End X coordinate.
            to_y: End Y coordinate.
            duration: How long the drag takes in seconds (default 0.5).
        """
        try:
            result = with_timeout(
                lambda: do_drag(from_x, from_y, to_x, to_y, duration=duration),
                timeout=5.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 5s dragging from ({from_x}, {from_y}) to ({to_x}, {to_y}). The UI may be frozen."

        from tools.screenshot import capture_screenshot
        shot = capture_screenshot()

        return [
            McpImage(data=_b64.b64decode(shot["image"]), format="png"),
            f"Dragged ({result['from_x']}, {result['from_y']}) -> ({result['to_x']}, {result['to_y']}). Screenshot: {shot['width']}x{shot['height']}",
        ]

    @server.tool()
    def hover(x: int, y: int) -> str:
        """Move the mouse cursor to a position without clicking. Useful for revealing tooltips.

        Parameters:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
        """
        try:
            result = with_timeout(
                lambda: do_hover(x, y),
                timeout=3.0,
            )
        except ActionTimeoutError:
            return f"Timed out after 3s hovering at ({x}, {y}). The UI may be frozen."
        return f"Hovered at ({result['x']}, {result['y']})."

    @server.tool()
    def get_mouse_position() -> str:
        """Get the current mouse cursor position.

        Returns the x, y pixel coordinates of the mouse cursor.
        Useful for debugging coordinate issues or confirming cursor placement.
        """
        try:
            result = with_timeout(do_get_mouse_position, timeout=2.0)
        except ActionTimeoutError:
            return "Timed out after 2s getting mouse position."
        return f"Mouse position: ({result['x']}, {result['y']})"

    return 7

