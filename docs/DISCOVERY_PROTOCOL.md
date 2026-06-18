# Discovery Protocol

Methodical UI discovery when a step-by-step flow fails to find a control.

## Loop

```
observe_ui → resolve_target → (if miss) plan_probes → apply_probe → repeat
```

Or use `discover_target_tool` to run the full loop with trace at `~/.handson/traces/discovery_{id}.json`.

## Probe types (revelation only)

| Probe | Purpose |
|-------|---------|
| verify_context | Confirm expected window/modal |
| rescan | Re-search with raw tree / remembered backend |
| list_modals | Check popup dialogs |
| expand_menu | Open menu bar items |
| switch_tab | Activate tab |
| expand_tree | Expand collapsed tree node |
| scroll_panel | Page down in scrollable area |
| access_key | Alt+key for Win32 menus |
| dismiss_overlay | Escape to close menu/popup |
| find_by_template | OpenCV match from image file |

**Safe mode** (default): blocks probes on DELETE, SAVE, EXIT, etc.

## When smart_find fails

1. `observe_ui_tool` — understand state
2. `plan_probes_tool` — see ranked probes with reasons
3. `apply_probe_tool` — one probe at a time
4. `smart_find` or `discover_target_tool`
5. On success: note in playbook which probe revealed the control

## Image search

`find_by_template_tool(image_path=..., highlight=true)` for icon-only buttons.

## Spy walk

`spy_walk_visible_tool` highlights visible elements one-by-one (paginated with `start_index`).
