# Changelog

## 0.2.2 — 2026-02-22

macOS support (alpha), cross-platform platform layer, Windows reliability fixes. 28 MCP tools.

> **macOS support is alpha.** Core tools work — screenshots, OCR, accessibility, window management, input — but it hasn't seen the same mileage as Windows yet. Expect rough edges.

### macOS Support
- New `handson_platform` abstraction layer (`darwin_backend` / `win32_backend`) for platform-specific code
- Screenshots via Quartz `CGWindowListCreateImage`
- OCR via Apple Vision framework (`VNRecognizeTextRequest`) — no extra install needed
- Accessibility via `AXUIElement` — find, click, and list UI elements natively
- Window management via `CGWindow` + `NSRunningApplication`
- Framework detection via bundle identifiers (Cocoa, Electron, Qt, Chromium, Java)
- Keyboard shortcuts via AppleScript System Events (more reliable than raw CGEvents)
- macOS permissions frontloaded at server startup (Accessibility + Screen Recording prompts)
- Cross-platform Python launcher (`start.sh`) with Windows Store alias detection

### Windows Improvements
- `set_target_window` / `get_target_window` — session-level target window auto-focus
- Clearing target window now auto-refocuses the host terminal
- `SetForegroundWindow` polling (500ms) to confirm focus before input lands
- `AttachThreadInput` + `BringWindowToTop` pattern replaces bare `SetForegroundWindow`
- Win32 imports guarded behind `sys.platform` checks for cross-platform safety
- DPI detection moved to platform layer

### Screenshot & OCR
- Screenshots auto-downscaled to 1280px wide (LANCZOS), JPEG transport (~119KB vs ~2MB)
- Screenshot diff detection for change-aware workflows
- OCR content-area scoring and dual-pass merge for reliability
- `near_y` disambiguation for OCR matches
- Process-name window matching for OCR scoping
- Shared `find_matching_window()` helper across OCR and UI automation

### Tests
- Full macOS test suite: accessibility, classify, framework, input, OCR, smoke
- Platform init tests for backend selection
- DPI tests updated for platform backend
- Integration `conftest.py` bootstraps venv site-packages standalone

## 0.1.0 — 2026-02-21

First public release. 26 MCP tools for screen capture and desktop automation.

### Vision & Input
- `screenshot` — screen capture with optional region crop and annotation overlays
- `wait_for_change` — poll until screen content changes (threshold-based pixel diff)
- `get_screen_size` — enumerate all connected monitors
- `click`, `type_text`, `send_keys`, `scroll`, `drag`, `hover` — full mouse and keyboard control
- `get_mouse_position` — read current cursor coordinates
- `batch_actions` — execute click/type/keys/scroll/wait sequences in a single call

### Accessibility Targeting
- `find_element` — locate UI elements by name and role via the Windows UI Automation tree
- `click_element` — find + click center in one step
- `list_elements` — dump the accessible element tree (configurable depth, optional role filter for full-tree walk)
- `get_focused_element` — check which widget has keyboard focus
- `smart_find` — tries UIA first, falls back to OCR automatically; reports framework hints when both fail

### OCR
- `find_text` — find text on screen (substring match)
- `click_text` — find + click Nth occurrence
- Optional `rapidocr-onnxruntime` backend for faster OCR (pure-Python, no external binary)
- Falls back to Windows.Media.Ocr when RapidOCR is not installed (zero-dependency)
- Multi-word phrase matching with automatic bounding box merging
- Dark background handling via automatic image inversion retry
- High-resolution display support (automatic downscaling for images >4096px)
- Adaptive gap tolerance that scales with font size and DPI

### Framework Detection
- `detect_framework` — identifies Qt, WPF, WinForms, Electron, UWP/WinUI, Chromium browsers, Win32/MFC, Java Swing, JavaFX, GTK
- Reports UIA support level and 3 actionable automation hints per framework
- Distinguishes Chromium browsers from Electron apps by process name

### Window & System Management
- `list_windows`, `focus_window`, `launch_app` — window management
- `virtual_desktop` — create/switch/close isolated virtual desktops
- `clipboard` — read/write system clipboard
- `manage_screenshots` — rolling cap with cleanup
- `configure_uac` — suppress/restore UAC prompts for unattended automation

### Safety
- Action timeouts on all blocking MCP tool operations
- Circuit breaker for consecutive failures
- DPI-aware coordinate system
- Stale screenshot handle auto-recovery after MCP reconnect

### Plugin Integration
- `/handson` slash command for guided session startup
- Built-in skill with targeting strategy, workflow patterns, and best practices
- Agent Guide and Framework Support reference docs

