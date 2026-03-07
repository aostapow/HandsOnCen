# HandsOn Agent Guide

Quick reference for Claude and other AI agents using HandsOn tools.

## Tool Selection Flow

Use this priority order when interacting with a GUI:

1. **`find_element` / `click_element`** — First choice. Uses the accessibility tree. Fast, precise, works on most standard widgets.
2. **`smart_find`** — When unsure. Tries accessibility first, falls back to OCR automatically.
3. **`find_text` / `click_text`** — OCR fallback. Use when accessibility can't see the element (custom widgets, canvas content). `click_text` auto-retries nearby offsets if the center click has no effect.
4. **`screenshot(region=...)` + visual inspection** — Last resort. Crop a region, read coordinates visually, click by position.

## Starting on a New App

1. Call `detect_framework` to understand what toolkit the app uses
2. Call `list_elements` to see what's accessible
3. If few elements found, try `list_elements(role="Button")` to search deeper
4. Check framework hints for tips (e.g., Electron may need accessibility flag)

## Focus Management

**Set a target window early.** Call `set_target_window("Browser")` (or whatever app you're automating) at the start of a session. This auto-focuses the target before every input action, preventing the terminal from stealing focus between tool calls.

Clear it when switching apps or when done: `set_target_window("")`.

## Coordinate System

Screenshots are downscaled to 1280px max width for transport. All tool coordinates use **screen coordinates** (physical pixels), not screenshot pixels.

- **Never estimate coordinates from the screenshot image** — they will be wrong
- Use `find_text` or `find_element` to get real screen coordinates for anything you see
- Use `screenshot(annotate=True)` to see a grid with screen-coordinate labels

## Browser Web Content

The accessibility tree only covers browser chrome (tabs, address bar, toolbar). Web page content is invisible to `find_element` / `click_element` / `list_elements`.

For web forms: **Tab between fields, never click contenteditable/textarea directly.** They often ignore mouse clicks.
- OCR click for buttons/links: `find_text("Submit")` → `click` at those coordinates
- `Tab` / `Shift+Tab` to move between form fields
- `clipboard(action="write", text="...")` then `send_keys("ctrl+v")` for text entry
- `scroll(x, y, "down", pages=1)` for page-at-a-time scrolling (uses PageDown/PageUp keys internally — DPI-independent)

## Prefer Keyboard Shortcuts Over Mouse

**Use `send_keys` with keyboard shortcuts whenever practical.** Shortcuts are faster, more reliable, and don't depend on element coordinates or screen layout:

- **New tab**: `send_keys("ctrl+t")` instead of clicking the + button
- **Close tab**: `send_keys("ctrl+w")` instead of clicking the X
- **Navigate back**: `send_keys("alt+left")` instead of finding the back button
- **Address bar**: `send_keys("ctrl+l")` or `send_keys("f6")` instead of clicking the URL bar
- **Save**: `send_keys("ctrl+s")` instead of File > Save
- **Select all + copy**: `send_keys("ctrl+a")` then `send_keys("ctrl+c")` instead of drag-selecting
- **Tab between form fields**: `send_keys("tab")` instead of clicking each field
- **Submit forms**: `send_keys("enter")` instead of clicking Submit
- **Switch apps**: `send_keys("alt+tab")` as an alternative to `focus_window`

Reserve mouse clicks for elements that have no keyboard shortcut (custom buttons, specific list items, canvas content).

## Common Patterns

### Navigate and Verify
```
click_element(name="Settings") → screenshot(region) to verify
```

### Data Entry
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

## When Done

**Call `focus_window(title="Claude")` as your last action** so the user sees you've finished. Without this, the user has no signal that you're done — the target app stays in the foreground and they'll be waiting.

## Tips

- Use `batch_actions` for click-type-enter sequences to reduce round-trips
- Use `screenshot(annotate=True)` to see element outlines and mouse position
- Multi-word OCR queries work: `find_text("Save As PDF")` matches adjacent words
- OCR automatically retries with image inversion for dark backgrounds
- The accessibility tree is DPI-aware — coordinates are always screen-absolute

