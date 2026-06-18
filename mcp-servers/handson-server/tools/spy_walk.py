"""Spy-style visible element walk with sequential highlight."""
from __future__ import annotations

from typing import Optional


def spy_walk_visible(
    window_title: Optional[str] = None,
    filter_role: str = "",
    start_index: int = 0,
    batch_size: int = 10,
    pause_ms: int = 800,
    include_offscreen: bool = False,
) -> dict:
    """Walk visible elements, highlighting each in reading order (y, x)."""
    elements: list[dict] = []

    try:
        from tools.spy_bridge import spy_tree, spy_available
        if spy_available():
            result = spy_tree(
                window_title or "",
                mode="control",
                max_depth=6,
                visible_only=not include_offscreen,
                role_filter=filter_role,
            )
            elements = result.get("elements", [])
    except Exception:
        pass

    if not elements:
        from tools.ui_automation import do_list_elements
        result = do_list_elements(
            window_title=window_title,
            max_depth=6,
            role=filter_role or None,
            include_offscreen=include_offscreen,
        )
        elements = result.get("elements", [])

    visible = []
    for e in elements:
        if not include_offscreen:
            if e.get("visible") is False:
                continue
            if e.get("is_offscreen"):
                continue
        w = e.get("width", 0)
        h = e.get("height", 0)
        if w <= 0 or h <= 0:
            continue
        visible.append(e)

    visible.sort(key=lambda e: (e.get("y", 0), e.get("x", 0)))
    total = len(visible)
    batch = visible[start_index:start_index + batch_size]
    walked = []

    for i, elem in enumerate(batch):
        idx = start_index + i
        try:
            from tools.highlight import highlight_element_dict
            highlight_element_dict(elem, duration_ms=pause_ms)
        except Exception:
            pass
        walked.append({
            "index": idx,
            "name": elem.get("name", ""),
            "role": elem.get("role", ""),
            "automation_id": elem.get("automation_id", ""),
            "x": elem.get("x", 0),
            "y": elem.get("y", 0),
            "width": elem.get("width", 0),
            "height": elem.get("height", 0),
        })

    next_index = start_index + len(batch) if start_index + len(batch) < total else None
    return {
        "total": total,
        "start_index": start_index,
        "batch_size": len(batch),
        "next_index": next_index,
        "elements": walked,
        "pause_ms": pause_ms,
    }
