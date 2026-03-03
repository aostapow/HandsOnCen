#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_JSON="${SCRIPT_DIR}/../.claude-plugin/plugin.json"
SERVER_DIR="$(cd "${SCRIPT_DIR}/../mcp-servers/handson-server" && pwd)"
VENV_DIR="${SERVER_DIR}/.venv"

# Find the right Python 3.10+ for this platform.
PYTHON=""
if [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* ]]; then
    # Windows: "python" is the real binary; "python3" is a Store alias.
    PYTHON="python"
else
    # macOS/Linux: find a versioned 3.10+ first, fall back to python3.
    for py in python3.13 python3.12 python3.11 python3.10; do
        if command -v "$py" &>/dev/null; then
            PYTHON="$(command -v "$py")"
            break
        fi
    done
    : "${PYTHON:=python3}"
fi

# Patch plugin.json to use the Python we found. This ensures the MCP
# server launches with the same Python that built the venv.
CURRENT_CMD=$(grep -o '"command": "[^"]*"' "$PLUGIN_JSON" 2>/dev/null | head -1 | sed 's/"command": "//;s/"//')
if [ -n "$CURRENT_CMD" ] && [ "$CURRENT_CMD" != "$PYTHON" ]; then
    if [[ "$OSTYPE" == msys* || "$OSTYPE" == cygwin* ]]; then
        sed -i "s|\"command\": \"${CURRENT_CMD}\"|\"command\": \"${PYTHON}\"|" "$PLUGIN_JSON"
    else
        sed -i '' "s|\"command\": \"${CURRENT_CMD}\"|\"command\": \"${PYTHON}\"|" "$PLUGIN_JSON"
    fi
    echo "[HandsOn] Patched plugin.json: ${CURRENT_CMD} → ${PYTHON}" >&2
fi

# Only install if venv doesn't exist
if [ ! -d "${VENV_DIR}" ]; then
    echo "[HandsOn] Installing dependencies..." >&2

    "$PYTHON" -m venv "${VENV_DIR}" 2>/dev/null || python -m venv "${VENV_DIR}"

    if [ -f "${VENV_DIR}/bin/pip" ]; then
        PIP="${VENV_DIR}/bin/pip"
    elif [ -f "${VENV_DIR}/Scripts/pip.exe" ]; then
        PIP="${VENV_DIR}/Scripts/pip.exe"
    fi

    "${PIP}" install -q -r "${SERVER_DIR}/requirements.txt"

    # Platform-specific dependencies
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "[HandsOn] Installing macOS dependencies (PyObjC)..." >&2
        "${PIP}" install -q \
            pyobjc-core \
            pyobjc-framework-Cocoa \
            pyobjc-framework-Quartz \
            pyobjc-framework-Vision \
            pyobjc-framework-ApplicationServices
    else
        echo "[HandsOn] Installing Windows dependencies..." >&2
        "${PIP}" install -q pywinauto pyvda
    fi

    echo "[HandsOn] Dependencies installed." >&2
fi

# macOS: Preflight permissions check (Accessibility + Screen Recording)
if [[ "$(uname)" == "Darwin" ]]; then
    if [ -f "${VENV_DIR}/bin/python3" ]; then
        VPYTHON="${VENV_DIR}/bin/python3"
    elif [ -f "${VENV_DIR}/bin/python" ]; then
        VPYTHON="${VENV_DIR}/bin/python"
    else
        VPYTHON="python3"
    fi

    "${VPYTHON}" -c "
import sys, subprocess

missing = []

# 1. Accessibility (pyautogui input + AXUIElement)
try:
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    if not AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}):
        missing.append('Accessibility')
except Exception:
    try:
        from ApplicationServices import AXIsProcessTrusted
        if not AXIsProcessTrusted():
            missing.append('Accessibility')
            subprocess.Popen(['open', 'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

# 2. Screen Recording (screenshots + window titles)
try:
    from Quartz import CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess
    if not CGPreflightScreenCaptureAccess():
        CGRequestScreenCaptureAccess()
        missing.append('Screen Recording')
except ImportError:
    pass

if missing:
    perms = ' and '.join(missing)
    print(f'[HandsOn] macOS permissions needed: {perms}', file=sys.stderr)
    print(f'[HandsOn] Grant access in System Settings > Privacy & Security,', file=sys.stderr)
    print(f'[HandsOn] then restart for changes to take effect.', file=sys.stderr)
else:
    print('[HandsOn] macOS permissions OK.', file=sys.stderr)
" 2>&1 || true
fi
