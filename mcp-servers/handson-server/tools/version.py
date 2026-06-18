"""Version tools -- installed version and update checks."""

from __future__ import annotations

import version_check


def register(server) -> int:
    """Register version tools on *server*. Returns the number of tools registered."""

    @server.tool()
    def check_version(force: bool = False) -> str:
        """Check whether a newer HandsOn version is available on GitHub.

        Parameters:
            force: When true, bypass the 24-hour cache and query GitHub now.
        """
        info = version_check.check_version(force=force)
        lines = [
            f"current: v{info.current_version}",
            f"latest: v{info.latest_version} ({info.source})",
            f"status: {'update available' if info.update_available else 'up to date'}",
            f"url: {info.release_url}",
        ]
        if info.update_available:
            lines.append(
                "update: git pull origin main in your HandsOnCen repo, then restart Cursor"
            )
        return "\n".join(lines)

    return 1
