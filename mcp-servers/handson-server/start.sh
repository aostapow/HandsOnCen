#!/usr/bin/env bash
# Cross-platform Python launcher for HandsOn MCP server.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* ]]; then
    # Windows: "python" is the real binary; "python3" is a Store alias.
    exec python "$SCRIPT_DIR/server.py" "$@"
else
    # macOS / Linux: try versioned pythons (3.10+) before generic python3.
    for py in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$py" &>/dev/null; then
            exec "$py" "$SCRIPT_DIR/server.py" "$@"
        fi
    done
    echo "[HandsOn] ERROR: No Python 3.10+ found. Install Python 3.10+ to use HandsOn." >&2
    exit 1
fi
