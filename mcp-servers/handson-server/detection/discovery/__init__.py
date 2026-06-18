"""Methodical UI discovery protocol — observe, plan probes, apply, verify."""

from detection.discovery.observer import observe_ui
from detection.discovery.planner import plan_probes
from detection.discovery.executor import apply_probe
from detection.discovery.runner import discover_target
from detection.discovery.resolver import resolve_target

__all__ = [
    "observe_ui",
    "plan_probes",
    "apply_probe",
    "discover_target",
    "resolve_target",
]
