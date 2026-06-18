# Detection Architecture — Layered Model

HandsOn resolves UI elements through **layers**, each available if the previous fails.

## Layer stack

```
-1  ObjectRepository   — UFT-style logical names + image templates
 0  StrategyMemory     — remembered backend/layer per object
 1  Native             — UIA, FlaUI, MSAA, Win32 HWND, JAB
 2  OCR dual           — RapidOCR + Windows OCR in parallel
 3  Visual             — OpenCV contours + OCR regions
 4  Agentic            — rich context for MCP agent reasoning
```

## Key tools

| Tool | Purpose |
|------|---------|
| `smart_find` | Full layer cascade; `agentic=true` for context on miss |
| `repo_find` / `repo_list` | Object repository lookup |
| `highlight_element` / `clear_highlight` | Spy-style red border |
| `spy_inspect` / `spy_tree` | Spy-grade UIA inspection |
| `build_detection_context` | Agentic See-Think-Act payload |

## Persistence

- `~/.handson/repositories/{app_id}.json` — object definitions
- `~/.handson/repositories/{app_id}/assets/` — crop, template, annotated images
- `~/.handson/strategy_memory.json` — winning strategies per object

## Sidecars

- `handson-uia-sidecar` — FlaUI UIA3 interaction
- `handson-spy-sidecar` — Spy-grade inspect + highlight overlay

Build: `mcp-servers\handson-spy-sidecar\build.cmd`
