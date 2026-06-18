"""MCP tools for methodical UI discovery protocol."""
from __future__ import annotations

import json
from typing import Optional


def register(server) -> int:
    from tools.safety import with_timeout, ActionTimeoutError
    from detection.discovery.observer import observe_ui
    from detection.discovery.planner import plan_probes
    from detection.discovery.executor import apply_probe
    from detection.discovery.runner import discover_target
    from detection.discovery.resolver import resolve_target
    from tools.template_match import find_by_template
    from tools.spy_walk import spy_walk_visible

    @server.tool()
    def observe_ui_tool(window_title: str = "", hints: str = "") -> str:
        """Structured UI observation snapshot (framework, tree, modals, fingerprint)."""
        hint_list = [h.strip() for h in hints.split(",") if h.strip()] if hints else []
        try:
            obs = with_timeout(
                lambda: observe_ui(window_title or None, hint_list or None),
                timeout=15.0,
            )
        except ActionTimeoutError:
            return "Timed out observing UI."
        lines = [
            f"Framework: {obs.get('framework')} ({obs.get('exe_name', '')})",
            f"Fingerprint: {obs.get('fingerprint')} named={obs.get('named_count')}/{obs.get('element_count')}",
            f"Foreground: {obs.get('foreground_window', obs.get('window_title', ''))}",
        ]
        if obs.get("modals"):
            lines.append(f"Modals/popups: {len(obs['modals'])}")
            for m in obs["modals"][:5]:
                lines.append(f"  - {m.get('title')}")
        if obs.get("menu_bars"):
            lines.append(f"Menu bars: {', '.join(m.get('name', '?') for m in obs['menu_bars'][:5])}")
        if obs.get("ocr_sample"):
            lines.append(f"OCR hints: {len(obs['ocr_sample'])} matches")
        lines.append(f"Screenshot: {obs.get('screenshot_path', '')}")
        return "\n".join(lines)

    @server.tool()
    def plan_probes_tool(
        goal: str,
        window_title: str = "",
        hints: str = "",
        expected_window: str = "",
        image_path: str = "",
        safe_mode: bool = True,
    ) -> str:
        """Ranked list of revelation probes with reasons (methodical, not random)."""
        hint_list = [h.strip() for h in hints.split(",") if h.strip()] if hints else ([goal] if goal else [])
        obs = observe_ui(window_title or None, hint_list)
        step_context = {"expected_window": expected_window} if expected_window else {}
        planned = plan_probes(
            goal=goal,
            hints=hint_list,
            observation=obs,
            step_context=step_context,
            safe_mode=safe_mode,
            image_path=image_path or None,
        )
        if not planned:
            return "No probes suggested — try observe_ui_tool first."
        lines = [f"Probes for '{goal}' ({len(planned)}):"]
        for i, p in enumerate(planned[:15]):
            lines.append(f"[{i}] {p['id']} target='{p.get('target', '')}' — {p['reason']} (risk={p['risk']})")
        return "\n".join(lines)

    @server.tool()
    def apply_probe_tool(
        probe_id: str,
        target: str = "",
        window_title: str = "",
        hints: str = "",
        safe_mode: bool = True,
    ) -> str:
        """Apply one revelation probe (expand menu, scroll, access key, etc.)."""
        hint_list = [h.strip() for h in hints.split(",") if h.strip()] if hints else []
        try:
            result = with_timeout(
                lambda: apply_probe(
                    probe_id=probe_id,
                    target=target,
                    window_title=window_title or None,
                    hints=hint_list,
                    safe_mode=safe_mode,
                ),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out applying probe."
        return json.dumps({
            "applied": result.get("applied"),
            "ui_changed": result.get("ui_changed"),
            "fingerprint_changed": result.get("fingerprint_changed"),
            "detail": result.get("detail"),
            "error": result.get("error"),
        }, indent=2)

    @server.tool()
    def discover_target_tool(
        goal: str,
        window_title: str = "",
        hints: str = "",
        role: str = "",
        automation_id: str = "",
        image_path: str = "",
        repo_path: str = "",
        expected_window: str = "",
        max_steps: int = 15,
        highlight_on_find: bool = True,
    ) -> str:
        """Methodical discovery loop: observe → resolve → plan → apply probes until found."""
        hint_list = [h.strip() for h in hints.split(",") if h.strip()] if hints else ([goal] if goal else [])
        step_context = {"expected_window": expected_window} if expected_window else {}
        try:
            result = with_timeout(
                lambda: discover_target(
                    hints=hint_list,
                    goal=goal,
                    role=role or None,
                    automation_id=automation_id or None,
                    window_title=window_title or None,
                    image_path=image_path or None,
                    repo_path=repo_path or None,
                    step_context=step_context,
                    max_steps=max_steps,
                    highlight_on_find=highlight_on_find,
                ),
                timeout=120.0,
            )
        except ActionTimeoutError:
            return "Timed out during discovery."
        if result.get("found"):
            e = result.get("element", {})
            return (
                f"Found via discovery (trace {result.get('trace_id')}):\n"
                f"  {e.get('role')} \"{e.get('name')}\" at ({e.get('x')},{e.get('y')})\n"
                f"  Probes tried: {', '.join(result.get('probes_tried', []))}\n"
                f"  Trace: {result.get('trace_path', '')}"
            )
        return (
            f"Not found after {result.get('steps')} steps (trace {result.get('trace_id')}).\n"
            f"Probes: {', '.join(result.get('probes_tried', []))}\n"
            f"Trace: {result.get('trace_path', '')}\n"
            f"Use plan_probes_tool / apply_probe_tool or build_detection_context."
        )

    @server.tool()
    def find_by_template_tool(
        image_path: str,
        window_title: str = "",
        threshold: float = 0.75,
        highlight: bool = False,
    ) -> str:
        """Find UI element by template image (icon/button screenshot)."""
        try:
            result = with_timeout(
                lambda: find_by_template(image_path, window_title or None, threshold),
                timeout=20.0,
            )
        except ActionTimeoutError:
            return "Timed out."
        if not result.get("found"):
            return f"Not found: {result.get('error', '')}"
        e = result["element"]
        if highlight:
            from tools.highlight import highlight_element_dict
            highlight_element_dict(e, duration_ms=3000)
        return (
            f"Template match {result.get('confidence', 0):.2f}: "
            f"({e['x']},{e['y']}) {e['width']}x{e['height']}"
        )

    @server.tool()
    def spy_walk_visible_tool(
        window_title: str = "",
        filter_role: str = "",
        start_index: int = 0,
        batch_size: int = 10,
        pause_ms: int = 800,
    ) -> str:
        """Walk visible elements highlighting each (Spy-style), paginated."""
        try:
            result = with_timeout(
                lambda: spy_walk_visible(
                    window_title=window_title or None,
                    filter_role=filter_role,
                    start_index=start_index,
                    batch_size=batch_size,
                    pause_ms=pause_ms,
                ),
                timeout=60.0,
            )
        except ActionTimeoutError:
            return "Timed out during spy walk."
        lines = [
            f"Spy walk: {result['start_index']}-{result['start_index'] + result['batch_size'] - 1} "
            f"of {result['total']} (pause {result['pause_ms']}ms)",
        ]
        for e in result.get("elements", []):
            lines.append(
                f"  [{e['index']}] {e['role']} \"{e['name']}\" "
                f"({e['x']},{e['y']}) {e['width']}x{e['height']}"
            )
        if result.get("next_index") is not None:
            lines.append(f"Next: spy_walk_visible_tool(start_index={result['next_index']})")
        return "\n".join(lines)

    return 6
