"""Unified target resolution."""
from __future__ import annotations

from typing import Any, Optional

from detection.layers.layered_detector import LayeredDetector, LocatorQuery, ResolveOptions


def resolve_target(
    hints: Optional[list[str]] = None,
    role: Optional[str] = None,
    automation_id: Optional[str] = None,
    window_title: Optional[str] = None,
    image_path: Optional[str] = None,
    repo_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve target via layered detector + optional template image."""
    from detection.orchestrator import get_orchestrator

    name = hints[0] if hints else ""
    orch = get_orchestrator()
    layered = LayeredDetector(orch)
    query = LocatorQuery(
        name=name or None,
        role=role,
        automation_id=automation_id,
        window_title=window_title,
        repo_path=repo_path,
    )
    opts = ResolveOptions(backend=backend, remember=False)
    result = layered.resolve(query, opts)

    if result.found:
        return result.to_dict()

    if image_path:
        from tools.template_match import find_by_template
        tmpl = find_by_template(image_path, window_title=window_title)
        if tmpl.get("found"):
            return {
                "found": True,
                "layer": "template",
                "backend": "template",
                "method": "template",
                "confidence": tmpl.get("confidence", 0.0),
                "elements": [tmpl["element"]],
            }

    return result.to_dict()
