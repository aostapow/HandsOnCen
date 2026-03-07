---
name: handson
description: Use when interacting with any GUI application, performing screen automation, UI testing, visual verification, or any task requiring screen capture and mouse/keyboard interaction
---

# HandsOn — Screen Automation Workflow

## Overview

You have eyes and hands. Use the HandsOn MCP tools to see the screen, click, type, scroll, and interact with any application. This skill teaches you how to use them effectively.

## Browser Tasks — Playwright Bridge

If Playwright MCP tools are available (`mcp__plugin_playwright_playwright__browser_*`), use them for all in-browser interactions. HandsOn handles everything outside the browser.

### What Goes Where

- **Playwright:** navigating URLs, clicking web elements, filling forms, reading page content, taking page screenshots, waiting for elements, running JS — anything inside a browser tab
- **HandsOn:** non-browser GUI apps, native dialogs (file pickers, download prompts, auth popups), and visual verification of what the user actually sees on screen

### The Desync Problem

By default, Playwright launches its own browser instance. This means Claude and the user are looking at **different browsers** — Playwright sees its browser, the user sees theirs. Visual verification with HandsOn will show the user's screen, not what Playwright is working on.

### Bridging: Connect Playwright to the User's Browser

To fix this, Playwright can attach to the user's existing browser instead of launching its own. Two approaches:

**Option A — Browser Extension (easiest):**
1. Install the "Playwright MCP Bridge" extension in Edge/Chrome
2. Reconfigure the Playwright plugin to add `--extension`:
   ```json
   { "args": ["@playwright/mcp@latest", "--browser", "msedge", "--extension"] }
   ```
3. Playwright now works on the user's actual browser tabs

**Option B — CDP Endpoint:**
1. Relaunch Edge with remote debugging: `msedge --remote-debugging-port=9222`
2. Reconfigure the Playwright plugin to add `--cdp-endpoint`:
   ```json
   { "args": ["@playwright/mcp@latest", "--cdp-endpoint", "ws://localhost:9222"] }
   ```
3. Playwright connects to the user's running browser

### The Bridge Workflow

**Initial connection:** When Playwright is configured with `--extension`, the browser extension shows a connection prompt ("Allow" / "Reject") that must be accepted before Playwright can work. The 30-second CDP timeout means you can't reliably click it manually.

**Recommended:** Set the `PLAYWRIGHT_MCP_EXTENSION_TOKEN` env var in the Playwright plugin config to bypass the dialog entirely:
```json
{
  "args": ["@playwright/mcp@latest", "--browser", "msedge", "--extension"],
  "env": { "PLAYWRIGHT_MCP_EXTENSION_TOKEN": "<token from extension page>" }
}
```
The token is shown on the extension's connection prompt page. Once set, connections auto-approve.

**Fallback:** If the token isn't set and the prompt appears, use HandsOn `click_text("Allow")` to approve — but this only works if the Playwright call hasn't already timed out.

**Once bridged, the interaction loop is:**

1. **HandsOn `screenshot`** — see what the user actually sees on screen
2. **Playwright `browser_snapshot`** — get the DOM/accessibility tree for precise interaction
3. **Playwright `browser_click` / `browser_type`** — interact with web elements via DOM
4. **HandsOn `screenshot`** — verify the result on the user's actual screen

This gives you DOM precision (Playwright) with visual ground truth (HandsOn).

### Fallback

**Always fall back to HandsOn for browser work if:**
- Playwright tools are not available in the session
- Playwright errors on any call (connection refused, extension not found, browser not running)
- Playwright shows a different page than what the user sees (not bridged)

Don't retry Playwright if it fails — switch to HandsOn immediately and use the Web Form Pattern below. The bridging setup is optional; HandsOn works fine for browser tasks on its own.

### Quick Check

To detect if bridging is active, try `browser_snapshot` — if it shows the same page the user has open (verify with a HandsOn screenshot), you're bridged. If it shows a different page or blank tab, Playwright is running its own browser.

## Before Starting

Establish permissions with the user:

1. **Autonomy level** — Should I ask before each action, or run fully autonomous?
2. **Elevated prompts** — Can I interact with UAC/sudo/admin dialogs?
3. **Destructive actions** — Can I close apps, delete files, overwrite content?
4. **Sensitive fields** — Can I type into password or API key fields?

Store the answers and operate within the granted scope for the session.

> **macOS:** Ensure your terminal has Accessibility permissions (System Settings > Privacy & Security > Accessibility). HandsOn checks this on startup and warns if not granted.

## Hands On / Hands Off

**Always announce intent and show a visible status when interacting with the screen.**

Before your first HandsOn tool call in a sequence:
1. **Announce intent in plain text** — tell the user what you're about to do and why. Example: *"I'll take a look at the screen to check the button placement."*
2. **Create a status task** with `TaskCreate`:
   - `subject`: Short description of what you're doing — e.g. `"Check button placement"`
   - `activeForm`: `"Hands On — checking button placement"` (always prefix with "Hands On — ")
3. Set it to `in_progress` with `TaskUpdate`

This displays a live spinner in the UI (e.g. `⟳ Hands On — checking button placement`) so the user always knows you're actively looking at their screen and what you're looking for.

When you're done with screen interaction:
1. Mark the task as `completed` with `TaskUpdate`

If you're doing multiple separate interaction sequences in one session, create a new task each time. Don't reuse completed ones.

## Starting on a New App

Before diving in, understand what you're working with:

1. **Call `detect_framework`** to identify the app's UI toolkit and get automation hints
2. **Call `list_elements`** to see what's accessible via the accessibility tree
3. If few elements found, try **`list_elements(role="Button")`** to search the full tree for a specific control type
4. **Read the framework hints** — they tell you what works and what doesn't for this specific toolkit

## Virtual Desktop Isolation (Optional)

By default, **work on the user's current desktop**. With accessibility targeting and OCR, you can precisely interact with elements without risk of misclicks. Working on the same desktop lets the user see everything you do in real-time.

Use `virtual_desktop` only when the user requests isolation, or for specific scenarios:
- **Automated test suites** that open/close many apps
- **CI/headless environments** where no user is watching
- **Sensitive workflows** where the user explicitly wants separation

If you do use virtual desktops, the host terminal is automatically pinned to all desktops so the user can always see your output.

**Note:** On macOS, desktop creation requires manual setup via Mission Control. On Linux, workspace navigation uses existing workspaces.

## Focus Management

**Set a target window early.** Call `set_target_window("Browser")` (or whatever app you're automating) at the start of a multi-step interaction. This auto-focuses the target before every input action, preventing the terminal from stealing focus between tool calls.

Clear it when switching apps or when done: `set_target_window("")`.

## Prefer Keyboard Shortcuts Over Mouse

**Use `send_keys` with keyboard shortcuts whenever practical.** Shortcuts are faster, more reliable, and don't depend on element coordinates or screen layout:

- **New tab**: `send_keys("ctrl+t")` — don't click the + button
- **Close tab**: `send_keys("ctrl+w")` — don't click the X
- **Navigate back**: `send_keys("alt+left")` — don't find the back button
- **Address bar**: `send_keys("ctrl+l")` — don't click the URL bar
- **Save**: `send_keys("ctrl+s")` — don't navigate File > Save
- **Select all + copy**: `send_keys("ctrl+a")` then `send_keys("ctrl+c")`
- **Tab between fields**: `send_keys("tab")` — don't click each field
- **Submit forms**: `send_keys("enter")` — don't click Submit
- **Switch apps**: `send_keys("alt+tab")` as alternative to `focus_window`
- **Open new browser tab for a URL**: `send_keys("ctrl+t")`, then type the URL — don't navigate in an existing tab (you might close the user's content)

> **macOS shortcuts:** On macOS, use `cmd` instead of `ctrl` for most shortcuts. For example: `cmd+t` (new tab), `cmd+w` (close tab), `cmd+l` (address bar), `cmd+s` (save), `cmd+a` then `cmd+c` (select all + copy), `cmd+v` (paste). Use `option` instead of `alt` (e.g., `option+left` for navigate back). HandsOn automatically detects the platform.

Reserve mouse clicks for elements that have no shortcut (custom buttons, specific list items, canvas content).

## Core Loop

Every interaction follows this pattern:

```
screenshot → analyze → act → wait_for_change → verify → repeat
```

1. **See first** — Always `screenshot` before any interaction. Never act blind.
2. **Analyze** — Describe what you see. Identify the element you need to interact with and estimate its coordinates.
3. **Act** — Use `click`, `type_text`, `send_keys`, `scroll`, `drag`, or `hover`.
4. **Wait** — Use `wait_for_change` after actions that modify the UI (clicking buttons, submitting forms, opening menus). Skip for hover or simple mouse moves.
5. **Verify** — The post-action screenshot (auto-returned by `click`/`drag`, or from `wait_for_change`) confirms whether the action succeeded.
6. **Adapt** — If the action didn't produce the expected result, retry with adjusted coordinates or try an alternative approach.

## Coordinate System

**CRITICAL:** Screenshots are downscaled to 1280px max width for transport. All tool coordinates use SCREEN coordinates (physical pixels), NOT screenshot pixels.

- Your screen may be 3840x2160 or 5120x2160, but screenshots appear as 1280px wide
- The screenshot is for **visual reference only** — never estimate click coordinates from the screenshot image
- **OCR tools** (`find_text`, `click_text`) return screen coordinates — use them directly
- **Accessibility tools** (`find_element`, `click_element`) return screen coordinates — use them directly
- When you see something in a screenshot and need to click it, use `find_text` or `find_element` to get real coordinates
- `screenshot(annotate=True)` overlays a grid with screen-coordinate labels for debugging

## Browser Web Content

The accessibility tree only exposes **browser chrome** (address bar, tabs, toolbar). Web page content (inputs, buttons, links, text fields, contenteditable areas) is **NOT** in the accessibility tree.

**Do NOT use** `find_element` / `click_element` / `list_elements` for web page content — they only see browser UI.

### Web Form Pattern (ALWAYS use this for forms)

1. **Navigate**: `ctrl+l` → type URL → `enter`
2. **Find the first field**: Use `find_text` to locate it by placeholder/label, click those OCR coordinates
3. **Move between fields**: `Tab` / `Shift+Tab` — **NEVER click contenteditable or textarea elements directly**, they often don't respond to mouse clicks. Tab is 100% reliable.
4. **Enter text**: Short text → `type_text`. Long text → clipboard paste (see below).
5. **Submit**: `send_keys("enter")` or `click_text("Submit")`

### Clipboard Paste for Long Text

`type_text` is slow and error-prone for anything over ~50 characters. Use clipboard paste:

```
clipboard(action="write", text="Your long content here...")
# Tab to the target field (don't try to click it)
send_keys("ctrl+v")  # On macOS: send_keys("cmd+v")
```

### Scrolling Web Pages

Use `scroll(x, y, direction, pages=1)` for page-at-a-time scrolling. The `pages` parameter uses **PageDown/PageUp keyboard presses** internally, which always scrolls exactly one page regardless of DPI or display scaling.

- `pages=1` — one full page (default when neither `pages` nor `amount` is given)
- `pages=0.5` — half page (uses arrow key presses)
- `pages=2` — two pages
- For fine mouse-wheel control, use `amount=N` with raw wheel clicks instead

**Important:** Mouse wheel scroll (`amount`) is unreliable on high-DPI displays — the same `amount` value scrolls different distances depending on DPI scaling. Always prefer `pages` for predictable scrolling.

## Tool Selection Guide

| I need to... | Use |
|---|---|
| **Targeting** | |
| Find a UI element reliably | `find_element` (by name/role in accessibility tree) |
| Find element with auto-fallback | `smart_find` (tries UIA first, then OCR automatically) |
| Click a UI element by name | `click_element` (find + click center) |
| See what's clickable | `list_elements` (dump accessible element tree) |
| Find all controls of a type | `list_elements(role="Button")` (full-tree walk filtered by type) |
| Check what has keyboard focus | `get_focused_element` (verify before typing) |
| Find text on screen (OCR) | `find_text` (for apps without accessibility) |
| Click visible text (OCR) | `click_text` (find + click, auto-retries nearby offsets if no response) |
| Identify app framework | `detect_framework` (returns toolkit + hints) |
| **Vision** | |
| See what's on screen | `screenshot` |
| Wait for UI to respond | `wait_for_change` |
| Debug coordinate issues | `screenshot(annotate=True)` (grid + crosshair + elements) |
| Get monitor dimensions | `get_screen_size` |
| Save reference for comparison | `screenshot_baseline` (capture before a change) |
| See what changed visually | `screenshot_diff` (highlights diff vs baseline in red overlay) |
| **Input** | |
| Press a button / select an item | `click` |
| Enter text in a field | `click` the field, then `type_text` |
| Use a keyboard shortcut | `send_keys` (e.g., "ctrl+s") |
| Navigate a long page/list | `scroll` |
| Move an element | `drag` |
| Check a tooltip or hover state | `hover` |
| Run a click-type-enter sequence | `batch_actions` (reduces round-trips) |
| **Windows & System** | |
| Lock focus to one app | `set_target_window` (auto-focuses before every input) |
| Check current target | `get_target_window` |
| Switch to a different app | `focus_window` |
| See what apps are open | `list_windows` |
| Open an application | `launch_app` |
| Read text from the UI reliably | `clipboard` (Ctrl+A, Ctrl+C, then clipboard read) |
| Copy content into the UI | `clipboard` write, then `send_keys` "ctrl+v" |
| Work on an isolated desktop | `virtual_desktop` (create, then close when done) |
| Check current mouse position | `get_mouse_position` |
| Manage UAC prompts | `configure_uac` (suppress/restore/status) |
| **Monitoring** | |
| Watch for new popups/dialogs | `start_watcher` (background thread polls for new windows) |
| Check what appeared | `get_notifications` (returns new windows with type + snippet) |
| Stop watching | `stop_watcher` |

## Targeting Strategy

Use this priority order:

1. **`find_element` / `click_element`** — First choice. Uses the accessibility tree. Fast, precise, DPI-aware. Works on most standard widgets.
2. **`smart_find`** — When unsure. Tries accessibility first, falls back to OCR automatically. Reports framework hints when both fail.
3. **`find_text` / `click_text`** — OCR fallback. Use when accessibility can't see the element (custom widgets, canvas content, GTK apps).
4. **`screenshot(region=...)` + visual inspection** — Last resort. Crop a region, read coordinates visually, click by position.

## Common Patterns

### Launching Shells and Terminal Commands

**Never use `launch_app("powershell", args="some-command")`** — the window opens, runs, and immediately closes before you can see output or interact.

Instead:
```
# Open an interactive shell (stays open):
launch_app("wt")                              # Windows Terminal (preferred)
launch_app("powershell", args="-NoExit")      # PowerShell that stays open

# Run a command AND keep the window open:
launch_app("powershell", args="-NoExit -Command Get-Process")
launch_app("wt", args="powershell -NoExit -Command Get-Process")

# Then type further commands into it:
set_target_window("PowerShell")
type_text("dir\n")
```

The key is **`-NoExit`** — without it, PowerShell runs the command and terminates. Same applies to `cmd /k` (stays open) vs `cmd /c` (closes).

### Data Entry with batch_actions
```
batch_actions([
    {"action": "click", "x": 100, "y": 200},
    {"action": "type", "text": "hello@example.com"},
    {"action": "keys", "keys": "tab"},
    {"action": "type", "text": "password123"},
    {"action": "keys", "keys": "enter"}
])
```

### Confirm Focus Before Typing
```
get_focused_element → verify it's the right field → type_text
```

### Find All Form Fields
```
list_elements(role="Spinner")   → all numeric inputs
list_elements(role="Edit")      → all text fields
list_elements(role="ComboBox")  → all dropdowns
```

## Error Recovery

- **Unexpected dialog/popup**: Screenshot it, read the message, decide whether to dismiss or act on it.
- **Wrong window in focus**: Use `focus_window` to bring the right one forward.
- **Click didn't register**: Try clicking again. If still failing, try clicking slightly offset coordinates.
- **App not responding**: Wait longer with `wait_for_change(timeout=10)`. If still stuck, report to user.
- **Lost context**: Take a fresh `screenshot` to re-establish where you are.
- **Element not found**: Run `detect_framework` to understand what toolkit the app uses and check the hints.

## When Done

**Call `focus_window(title="Claude")` as your last action** so the user sees you've finished. Without this, the user has no signal that you're done — the target app stays in the foreground and they'll be waiting.

## Best Practices

- **Set target window first** — Call `set_target_window` at the start of a session to prevent terminal focus-stealing.
- **Keyboard shortcuts over mouse** — Use `send_keys("ctrl+t")`, `send_keys("ctrl+l")`, etc. whenever a shortcut exists. Faster and more reliable than clicking.
- **Open new tabs, don't hijack** — Use `ctrl+t` before navigating to a URL. The user may have content open in the current tab.
- **Full screen screenshots by default** — Don't tunnel-vision on one window. Errors and popups appear elsewhere.
- **Verify every state change** — Never assume an action worked. Always confirm visually.
- **Use `smart_find` over `find_element`** — It handles the UIA-to-OCR fallback automatically.
- **Use `batch_actions` for sequences** — Reduces round-trips for click-type-enter flows.
- **Use clipboard for text extraction** — It's more reliable than trying to visually parse small text from screenshots.
- **Multi-word OCR queries work** — `find_text("Save As PDF")` matches adjacent words automatically.
- **OCR handles dark backgrounds** — Automatic image inversion retry when text isn't found.
- **OCR handles high-res displays** — Automatic downscaling for screenshots >4096px.
- **Clean up** — Call `manage_screenshots(action="cleanup")` when you're done with a long session.
- **Report what you see** — When describing UI state to the user, be specific about what elements are visible and their apparent state.

## Playbook — Self-Learning Patterns

You maintain a persistent playbook at `~/.claude/handson/playbook.md` that accumulates patterns learned from UI automation sessions. This helps you avoid repeating mistakes and get better over time.

### Session Start
At the beginning of any HandsOn session, check if the playbook exists:
1. Read `~/.claude/handson/playbook.md` using the Read tool
2. If it exists, review the patterns before starting work
3. Apply relevant patterns to your current task

### When to Write
After completing a multi-step GUI workflow that involved:
- Retries or corrections (something didn't work the first time)
- Non-obvious techniques (keyboard shortcuts, specific element targeting)
- Window-matching lessons (which title strings work for which apps)

### What to Write
Entries must be **actionable and terse** — one line per pattern, grouped by app:

```markdown
# HandsOn Playbook
<!-- Auto-maintained by Claude. Max 200 lines. Compact when exceeded. -->

## <App Name> (<Browser/Context>)
- <actionable pattern, 1 line>

## General
- <cross-app pattern>
```

### Size Limit
Keep the playbook under **200 lines**. When it exceeds 200 lines:
1. Merge entries for the same app
2. Remove patterns that haven't been useful
3. Prefer general patterns over app-specific ones when they overlap

