# HandsOn

[![GitHub release](https://img.shields.io/github/v/release/3spky5u-oss/HandsOn?style=flat-square)](https://github.com/3spky5u-oss/HandsOn/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey?style=flat-square)]()
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-blueviolet?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![MCP](https://img.shields.io/badge/MCP-server-orange?style=flat-square)](https://modelcontextprotocol.io)
[![Tools](https://img.shields.io/badge/tools-34-green?style=flat-square)]()

Give Claude eyes and hands. A Claude Code plugin that lets Claude see your screen and interact with any application on your desktop.

<!-- TODO: ![Demo GIF](docs/demo.gif) -->

> **Alpha software.** HandsOn works and is genuinely useful, but Claude will sometimes stumble through tasks — misclicking sidebar links, scrolling the wrong container, needing multiple attempts to find the right element. Complex multi-step workflows (like filling out a Reddit post) may take several retries to get right. It's getting better with each release, but set your expectations accordingly.

## What's New in v0.3.0

- **Window-cropped visual detection** — When a target window is set, visual analysis is cropped to that window's bounds, eliminating noise from the terminal and other background apps
- **30-50% token reduction** — Compact output across all tools: shorter class names, removed redundant formatting, tighter coordinate notation
- **Unnamed element filtering** — `list_elements` now skips unnamed Pane/Group/Custom elements that add noise without value (common in Steam, Electron apps, etc.)
- **Process-tree terminal refocus** — `set_target_window("")` walks the process tree to find and refocus the host terminal instead of guessing by title
- **Immediate window focus** — `set_target_window()` now focuses the target window immediately on set, not just before the next input action
- **Visual detect module** — New CV-based UI region detection for apps with limited accessibility support
- **Self-correcting click** — `click_text` automatically retries at offset positions when the initial center click produces no visual change

## Why HandsOn?

Claude Code is powerful, but it's blind — it can't see your screen or interact with anything outside the terminal. HandsOn changes that. It gives Claude eyes to see what's on your desktop and hands to interact with it, turning it into a general-purpose desktop assistant.

**The core idea:** Claude can now do anything you can do at a keyboard and mouse — navigate apps, fill out forms, click through wizards, manage windows, launch programs, and verify its own work visually.

**What this enables:**

- **Desktop automation** — Automate any application on your computer, even legacy apps with no API
- **Visual verification** — Claude can see the result of its own work, catch visual bugs, and fix them without you describing what's wrong
- **App interaction** — Navigate settings, install software, fill out forms, click through dialogs — anything you'd normally alt-tab to do yourself
- **Accessibility-first targeting** — Uses the platform accessibility tree — Windows UI Automation (UIA) or macOS AXUIElement — not just pixel coordinates, so element targeting is DPI-aware and resolution-independent
- **Automatic fallbacks** — When accessibility doesn't work (custom widgets, canvas apps, games), it falls back to OCR, then to visual analysis. `smart_find` picks the right approach automatically.
- **Framework-aware** — Detects Qt, WPF, Electron, WinForms, etc., and tells Claude exactly what will and won't work

## Quick Start

### Install

```bash
# From GitHub (recommended)
claude plugin marketplace add 3spky5u-oss/HandsOn
claude plugin install handson

# From GitLab
claude plugin marketplace add git@gitlab.com:3spky5u/HandsOn.git
claude plugin install handson

# From Codeberg
claude plugin marketplace add git@codeberg.org:3spky5u/HandsOn.git
claude plugin install handson
```

Restart Claude Code after installing. Python dependencies are installed automatically on first run.

To update:
```bash
claude plugin marketplace update handson
claude plugin update handson
```

**Requirements:** Python 3.10+, Windows 10/11 or macOS 12+ (Monterey or later).

**Optional (Playwright bridge for browser tasks):**
If you also have the [Playwright MCP plugin](https://www.npmjs.com/package/@anthropic-ai/claude-code-playwright) installed, HandsOn automatically defers to Playwright for in-browser interactions (DOM access, form filling, page navigation) and reserves itself for desktop apps, native dialogs, and visual verification. For the best experience, connect Playwright to your existing browser using the `--extension` flag or `--cdp-endpoint` — this lets Playwright work on the same browser you see, with HandsOn verifying the result on your actual screen. See the [skill guide](skills/handson/SKILL.md) for setup details.

**Optional (faster OCR):**
```bash
pip install rapidocr-onnxruntime
```
When installed, OCR uses RapidOCR (fast, pure-Python) instead of Windows.Media.Ocr. Without it, the built-in Windows OCR engine works with zero extra dependencies.

On macOS, HandsOn uses the built-in Vision framework for OCR (no extra install needed). RapidOCR still works as a cross-platform alternative if preferred.

### Try It

Tell Claude to do something on your desktop:

```
"Open the Settings app and check what display resolution I'm running"
"Launch my app, fill out the form with test data, submit it, and verify the result"
"Open localhost:3000, screenshot it, and fix anything that looks off"
"Click through every tab in my app and tell me if anything looks broken"
"Install this .exe — click through the wizard and accept the defaults"
```

Use `/handson` to start a guided automation session with permission prompts.

## Tools

HandsOn provides 34 tools across 12 categories:

| Category | Tools | What They Do |
|----------|-------|--------------|
| **Vision** | `screenshot`, `wait_for_change`, `get_screen_size` | Capture the screen, detect when something changes, get monitor dimensions |
| **Visual Diff** | `screenshot_baseline`, `screenshot_diff` | Before/after screenshot comparison — highlights changed pixels in red with bounding box |
| **Input** | `click`, `type_text`, `send_keys`, `scroll`, `drag`, `hover`, `get_mouse_position` | Full mouse and keyboard control — click anywhere, type text, send hotkeys, scroll, drag |
| **Accessibility** | `find_element`, `click_element`, `list_elements`, `get_focused_element`, `smart_find` | Find and interact with UI elements via the Windows accessibility tree (UIA). `smart_find` auto-falls back to OCR |
| **OCR** | `find_text`, `click_text` | Find and click text on screen when the accessibility tree can't see it (games, custom widgets, canvas apps) |
| **Framework** | `detect_framework` | Identify the app's UI toolkit and get actionable automation hints |
| **Windows** | `list_windows`, `focus_window`, `launch_app`, `set_target_window`, `get_target_window` | List open windows, focus/minimize/maximize, launch apps. Target window auto-focuses before every input action |
| **Monitoring** | `start_watcher`, `stop_watcher`, `get_notifications` | Background thread watches for new windows/dialogs/toasts and captures snippets |
| **Automation** | `batch_actions` | Chain multiple actions (click, type, keypress, scroll, wait) in a single call — reduces round trips |
| **Desktop** | `virtual_desktop` | Create an isolated virtual desktop so Claude can work without disturbing your windows |
| **Utility** | `clipboard`, `manage_screenshots` | Read/write the clipboard, manage screenshot storage |
| **System** | `configure_uac` | Suppress UAC prompts for unattended automation workflows |

## How It Works

HandsOn uses a layered targeting strategy — it tries the most reliable method first and automatically falls back:

```
smart_find("Submit")
    |
    v
1. Accessibility tree (UIA)     -- fast, precise, DPI-aware
    |  not found?
    v
2. OCR text recognition         -- finds any visible text
    |  not found?
    v
3. Framework detection          -- tells you WHY it failed and what to try
```

**Layer 1: Accessibility (UIA / AXUIElement)** — `find_element`, `click_element`, `list_elements` query the accessibility tree (Windows UIA or macOS AXUIElement). This is the gold standard: elements have names, roles, bounding boxes, and it works regardless of DPI or window position.

**Layer 2: OCR** — `find_text`, `click_text` capture a screenshot and run OCR to find text. Handles dark backgrounds (automatic image inversion retry), high-res displays (automatic downscaling for >4096px), and multi-word phrases. Uses RapidOCR when installed, otherwise Windows.Media.Ocr.

**Layer 3: Framework detection** — `detect_framework` identifies the app's toolkit by inspecting window class names, process names, and loaded DLLs. Returns the UIA support level and 3 actionable hints (e.g., "Electron app detected. If elements aren't found, the app may need --force-renderer-accessibility flag").

**Layer 4: Vision** — `screenshot` feeds the screen directly to Claude's visual understanding for everything else (custom-painted controls, canvas content, image-based UIs, games).

## Framework Support

HandsOn auto-detects and adapts to 10 UI frameworks:

| Framework | UIA Support | Notes |
|-----------|------------|-------|
| WPF | Full | Best UIA support. Use AutomationId for reliable targeting. |
| UWP/WinUI | Full | XAML controls fully accessible. Flyouts may be separate windows. |
| JavaFX | Full | Native UIA support for standard controls. |
| Qt5/Qt6 | Partial | Standard widgets work. Custom QWidgets without QAccessibleInterface need OCR. |
| WinForms | Partial | Standard controls work. Owner-drawn and custom UserControls need OCR. |
| Win32/MFC | Partial | Common Controls work. Owner-drawn buttons need OCR. |
| Electron | Conditional | Needs `--force-renderer-accessibility` flag. Canvas content needs OCR. |
| Chromium browsers | Conditional | Auto-distinguished from Electron apps. Standard page elements work. |
| Java Swing | None (UIA) | UIA doesn't work — needs Java Access Bridge (`jabswitch -enable`) or OCR. |
| GTK | None | No UIA support on Windows. OCR and coordinate-based automation only. |

See [Framework Support Reference](docs/FRAMEWORK_SUPPORT.md) for per-framework troubleshooting.

### macOS Framework Support

| Framework | Accessibility | Notes |
|-----------|--------------|-------|
| Cocoa (native) | Full | Native AXUIElement support. All Apple apps. |
| Electron | Conditional | Accessibility may need to be enabled. Canvas content needs OCR. |
| Chromium browsers | Conditional | Standard page elements work via accessibility. |
| Qt | Partial | Standard widgets accessible. Custom widgets need OCR. |
| Java (JetBrains, etc.) | Partial | Depends on Java Accessibility Bridge. |
| Terminal apps | Full | Input goes through pyautogui passthrough. |

## Example Workflows

**General desktop automation:**
> "Open the Settings app, navigate to Display, and tell me what resolution I'm running at"

Claude launches Settings, uses UIA to navigate menus, reads the display resolution.

**App interaction:**
> "Open my app, click through each tab, fill out the contact form with test data, submit it, and tell me if anything looks broken"

Claude launches the app, detects its framework, navigates via accessibility tree, fills out forms, clicks submit, and reports any visual or functional issues.

**Visual QA — Claude sees its own work:**
> "Build me a settings page with a dark theme toggle, then open it in the browser, screenshot it, and fix anything that doesn't look right"

Claude writes the code, launches the dev server, opens the browser, takes a screenshot, spots that the toggle is misaligned, and fixes the CSS — all without you saying a word.

**Legacy apps with no accessibility:**
> "This old Java app has no accessibility. Find the 'Run Analysis' button and click it"

Claude detects Java Swing, knows UIA won't work, uses OCR to find the button text, and clicks it.

## Known Limitations

- **Windows and macOS only.** Linux is not currently supported. On macOS, ensure Accessibility permissions are granted to your terminal (System Settings > Privacy & Security > Accessibility).
- **Python 3.10+ required.** The MCP server uses modern type syntax.
- **Electron apps need a flag.** Most Electron apps disable accessibility by default. Relaunch with `--force-renderer-accessibility`.
- **Java Swing needs JAB.** UIA doesn't work with Swing. Enable Java Access Bridge (`jabswitch -enable`) or use OCR as the primary approach.
- **OCR sees everything on screen.** If your terminal and target app are both visible, OCR may find text in both. Use region screenshots to isolate the target window.

## Documentation

- [Agent Guide](docs/AGENT_GUIDE.md) — Quick reference for Claude/agents using HandsOn tools
- [Framework Support](docs/FRAMEWORK_SUPPORT.md) — Per-framework compatibility and troubleshooting

## Acknowledgments

HandsOn was inspired by:

- **[Empirica](https://github.com/Nubaeon/empirica)** by Nubaeon (David S. L. Van Assche) — for pioneering the SVG badge approach in Claude Code plugins, and for ideas around session-aware tooling
- **[mcp-pyautogui](https://github.com/hathibelagal-dev/mcp-pyautogui)** by hathibelagal-dev — for demonstrating that PyAutoGUI + MCP is a viable approach to desktop automation
- **[MCPControl](https://github.com/claude-did-this/MCPControl)** by claude-did-this — for showing how to give AI agents full Windows desktop control

HandsOn is an independent implementation with no shared code, built from the ground up with accessibility-first targeting, OCR fallback, framework detection, and native Claude Code plugin integration.

## License

MIT
