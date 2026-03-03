"""Target window auto-focus -- session state for multi-window workflows.

When a target window is set, every input action (click, type, keys, scroll,
drag, hover) will auto-focus that window before executing.  This eliminates
the need to call ``focus_window`` before every interaction when the terminal
keeps stealing focus between tool calls.

Provides two MCP tools:
    set_target_window  - set (or clear) the target window title
    get_target_window  - return the current target window title
"""

import sys
from typing import Optional

_target_window: Optional[str] = None


def _refocus_host_terminal() -> None:
    """Bring the host terminal back to the foreground."""
    try:
        from tools.windows import do_focus_window
        if sys.platform == "darwin":
            # Try common terminal apps; the one that's running will match
            for name in ("Terminal", "iTerm2", "Ghostty", "Alacritty", "kitty", "Warp"):
                result = do_focus_window(name, action="focus")
                if result.get("success"):
                    return
        else:
            # Windows: try env var first, then common terminal apps
            import os
            title = os.environ.get("CLAUDE_TERMINAL_TITLE", "")
            if title:
                result = do_focus_window(title, action="focus")
                if result.get("success"):
                    return
            for name in ("Windows Terminal", "PowerShell", "Command Prompt",
                         "cmd.exe", "Cmder", "Hyper", "Alacritty", "kitty"):
                result = do_focus_window(name, action="focus")
                if result.get("success"):
                    return
    except Exception:
        pass


def set_target(title: Optional[str]) -> None:
    """Set (or clear) the target window for auto-focus."""
    global _target_window
    was_set = _target_window is not None
    if title is not None and title.strip() == "":
        title = None
    _target_window = title
    if title:
        print(f"[target_window] Target set: {title!r}", file=sys.stderr)
    else:
        print("[target_window] Target cleared", file=sys.stderr)
        if was_set:
            _refocus_host_terminal()


def get_target() -> Optional[str]:
    """Return the current target window title, or ``None``."""
    return _target_window


def ensure_focus() -> None:
    """If a target window is set, focus it before an input action."""
    if _target_window is None:
        return
    from tools.windows import do_focus_window
    do_focus_window(_target_window, action="focus")


# ------------------------------------------------------------------
# MCP tool registration
# ------------------------------------------------------------------

def register(server) -> int:
    """Register the target-window tools on *server*. Returns 2."""

    @server.tool()
    def set_target_window(title: str = "") -> str:
        """Set or clear the target window for automatic focus.

        When set, every input action (click, type_text, send_keys, scroll,
        drag, hover) will auto-focus this window before executing.  This
        prevents the terminal from stealing focus between tool calls.

        When cleared (empty string), the host terminal is automatically
        brought back to the foreground. Always clear the target when you
        are done interacting with a GUI application.

        Parameters:
            title: Partial window title to match (case-insensitive).
                   Pass empty string to clear the target.
        """
        set_target(title if title else None)
        current = get_target()
        if current:
            return f"Target window set to {current!r}. All input actions will auto-focus this window."
        return "Target window cleared. Terminal refocused."

    @server.tool()
    def get_target_window() -> str:
        """Get the current target window for automatic focus.

        Returns the partial title being used for auto-focus, or a message
        indicating no target is set.
        """
        current = get_target()
        if current:
            return f"Target window: {current!r}"
        return "No target window set."

    return 2
