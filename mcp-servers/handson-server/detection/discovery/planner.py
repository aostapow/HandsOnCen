"""Ranked probe planning for discovery."""
from __future__ import annotations

from typing import Any, Optional

from detection.discovery.probes import ProbeSpec, default_probe_order, is_safe_target
from detection.strategy_memory import get_strategy, make_key


def plan_probes(
    goal: str = "",
    hints: Optional[list[str]] = None,
    observation: Optional[dict] = None,
    step_context: Optional[dict] = None,
    safe_mode: bool = True,
    image_path: Optional[str] = None,
) -> list[dict]:
    """Return ordered probe list with reasons (methodical, not random)."""
    hints = hints or ([goal] if goal else [])
    obs = observation or {}
    framework = obs.get("framework", "unknown")
    step_context = step_context or {}
    probes: list[ProbeSpec] = []

    expected_window = step_context.get("expected_window") or obs.get("foreground_window") or ""
    if expected_window:
        probes.append(ProbeSpec(
            id="verify_context",
            target=expected_window,
            reason="Confirm we are on the expected window before revealing UI",
            risk="low",
            revert="",
        ))

    probes.append(ProbeSpec(
        id="rescan",
        target=hints[0] if hints else goal,
        reason="Re-scan with raw tree and offscreen before changing UI state",
        risk="low",
        revert="",
        params={"tree_mode": "raw", "include_offscreen": True},
    ))

    if obs.get("modals"):
        for modal in obs["modals"][:3]:
            title = modal.get("title", "")
            probes.append(ProbeSpec(
                id="list_modals",
                target=title,
                reason=f"Target may be in popup/modal window '{title}'",
                risk="low",
                revert="",
            ))

    order = default_probe_order(framework)
    for menu in obs.get("menu_bars", [])[:5]:
        name = menu.get("name") or "Menu"
        if "expand_menu" in order and is_safe_target(name, safe_mode):
            probes.append(ProbeSpec(
                id="expand_menu",
                target=name,
                reason=f"Menu bar '{name}' may hide target until expanded",
                risk="low",
                revert="dismiss_overlay",
            ))

    for tab in obs.get("tabs", [])[:5]:
        name = tab.get("name") or ""
        if name and "switch_tab" in order and is_safe_target(name, safe_mode):
            probes.append(ProbeSpec(
                id="switch_tab",
                target=name,
                reason=f"Tab '{name}' may contain hidden controls",
                risk="low",
                revert="dismiss_overlay",
            ))

    for tree in obs.get("trees", [])[:3]:
        name = tree.get("name") or "Tree"
        if "expand_tree" in order:
            probes.append(ProbeSpec(
                id="expand_tree",
                target=name,
                reason=f"Expand collapsed tree '{name}' to reveal children",
                risk="low",
                revert="dismiss_overlay",
            ))

    if "scroll_panel" in order:
        probes.append(ProbeSpec(
            id="scroll_panel",
            target="",
            reason="Target may be outside viewport; scroll main panel",
            risk="low",
            revert="",
        ))

    for elem in obs.get("tree_sample", []):
        ak = elem.get("access_key") or elem.get("raw_properties", {}).get("access_key", "")
        if ak and "access_key" in order:
            probes.append(ProbeSpec(
                id="access_key",
                target=ak,
                reason=f"Try access key '{ak}' for Win32-style menu",
                risk="low",
                revert="dismiss_overlay",
                params={"keys": f"%{ak.lower()}"},
            ))
            break

    if image_path:
        probes.append(ProbeSpec(
            id="find_by_template",
            target=image_path,
            reason="Visual template match for icon/image-only control",
            risk="low",
            revert="",
            params={"image_path": image_path, "threshold": 0.75},
        ))

    app_name = obs.get("exe_name") or obs.get("foreground_window") or "foreground"
    mem_key = make_key(app_name, obs.get("window_title", ""), hints[0] if hints else goal)
    strat = get_strategy(mem_key)
    if strat and strat.get("preferred_backend"):
        probes.insert(1, ProbeSpec(
            id="rescan",
            target=hints[0] if hints else goal,
            reason=f"Retry with remembered backend {strat['preferred_backend']}",
            risk="low",
            revert="",
            params={"backend": strat["preferred_backend"]},
        ))

    # Dedupe by id+target
    seen = set()
    unique: list[ProbeSpec] = []
    for p in probes:
        key = (p.id, p.target)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    return [
        {
            "id": p.id,
            "target": p.target,
            "reason": p.reason,
            "risk": p.risk,
            "revert": p.revert,
            "params": p.params,
        }
        for p in unique
    ]
