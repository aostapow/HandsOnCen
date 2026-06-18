"""Discovery loop orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from detection.discovery.executor import apply_probe
from detection.discovery.observer import observe_ui
from detection.discovery.planner import plan_probes
from detection.discovery.resolver import resolve_target
from detection.discovery.tracer import append_step, new_trace_id


@dataclass
class DiscoverResult:
    found: bool = False
    trace_id: str = ""
    steps: int = 0
    element: Optional[dict] = None
    resolve: Optional[dict] = None
    trace_path: str = ""
    probes_tried: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "found": self.found,
            "trace_id": self.trace_id,
            "steps": self.steps,
            "element": self.element,
            "resolve": self.resolve,
            "trace_path": self.trace_path,
            "probes_tried": self.probes_tried,
            "error": self.error,
        }


def discover_target(
    hints: Optional[list[str]] = None,
    goal: str = "",
    role: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    image_path: Optional[str] = None,
    repo_path: Optional[str] = None,
    step_context: Optional[dict] = None,
    max_steps: int = 15,
    safe_mode: bool = True,
    highlight_on_find: bool = True,
) -> dict:
    """Methodical discovery loop with auditable trace."""
    hints = hints or ([goal] if goal else [])
    trace_id = new_trace_id()
    probes_tried: list[str] = []
    trace_path = ""

    for step in range(max_steps):
        obs = observe_ui(window_title=window_title, hints=hints)
        trace_path = str(append_step(trace_id, {"phase": "observe", "step": step, "observation": {
            "framework": obs.get("framework"),
            "fingerprint": obs.get("fingerprint"),
            "named_count": obs.get("named_count"),
        }}))

        resolved = resolve_target(
            hints=hints,
            role=role,
            automation_id=automation_id,
            window_title=window_title,
            image_path=image_path,
            repo_path=repo_path,
        )
        append_step(trace_id, {"phase": "resolve", "step": step, "result": {
            "found": resolved.get("found"),
            "layer": resolved.get("layer"),
            "backend": resolved.get("backend"),
        }})

        if resolved.get("found") and resolved.get("elements"):
            elem = resolved["elements"][0]
            if highlight_on_find:
                try:
                    from tools.highlight import highlight_element_dict
                    highlight_element_dict(elem, duration_ms=3000)
                except Exception:
                    pass
            try:
                from detection.object_snapshot import capture_object_snapshot
                from tools.framework_detect import do_detect_framework
                fw = do_detect_framework(window_title)
                capture_object_snapshot(
                    elem,
                    window_title=window_title,
                    repo_path=repo_path,
                    app_name=fw.get("process_name") or fw.get("exe_name") or "foreground",
                    exe_path=fw.get("exe_path", ""),
                    highlight=False,
                )
            except Exception:
                pass
            return DiscoverResult(
                found=True,
                trace_id=trace_id,
                steps=step + 1,
                element=elem,
                resolve=resolved,
                trace_path=trace_path,
                probes_tried=probes_tried,
            ).to_dict()

        planned = plan_probes(
            goal=goal,
            hints=hints,
            observation=obs,
            step_context=step_context,
            safe_mode=safe_mode,
            image_path=image_path,
        )
        remaining = [p for p in planned if p["id"] not in probes_tried or p.get("target")]
        if not remaining:
            break

        probe = remaining[0]
        probe_key = f"{probe['id']}:{probe.get('target', '')}"
        if probe_key in probes_tried:
            # skip duplicates, try next
            for p in remaining[1:]:
                pk = f"{p['id']}:{p.get('target', '')}"
                if pk not in probes_tried:
                    probe = p
                    probe_key = pk
                    break
            else:
                break

        probes_tried.append(probe_key)
        apply_result = apply_probe(
            probe_id=probe["id"],
            target=probe.get("target", ""),
            params=probe.get("params"),
            window_title=window_title,
            hints=hints,
            safe_mode=safe_mode,
        )
        append_step(trace_id, {"phase": "apply_probe", "step": step, "probe": probe, "result": {
            "applied": apply_result.get("applied"),
            "ui_changed": apply_result.get("ui_changed"),
        }})

        if probe.get("revert") and apply_result.get("applied"):
            pass  # revert deferred until next iteration or explicit dismiss

    # Final agentic context
    try:
        from detection.orchestrator import get_orchestrator
        from detection.layers.layered_detector import LocatorQuery
        ctx = get_orchestrator().build_detection_context(
            name=hints[0] if hints else goal,
            window_title=window_title,
        )
    except Exception:
        ctx = {}

    return DiscoverResult(
        found=False,
        trace_id=trace_id,
        steps=max_steps,
        trace_path=trace_path,
        probes_tried=probes_tried,
        error="Target not found after methodical discovery",
        resolve={"agentic_context": ctx},
    ).to_dict()
