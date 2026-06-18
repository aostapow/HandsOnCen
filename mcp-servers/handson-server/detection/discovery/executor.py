"""Execute single discovery probes."""
from __future__ import annotations

from typing import Any, Optional

from detection.discovery.observer import observe_ui


def apply_probe(
    probe_id: str,
    target: str = "",
    params: Optional[dict] = None,
    window_title: Optional[str] = None,
    hints: Optional[list[str]] = None,
    safe_mode: bool = True,
) -> dict[str, Any]:
    """Apply one revelation probe and return observation delta."""
    params = params or {}
    hints = hints or []
    before_fp = ""
    try:
        from tools.ui_automation import do_ui_fingerprint
        before_fp = do_ui_fingerprint(window_title=window_title).get("hash", "")
    except Exception:
        pass

    applied = False
    error = ""
    detail: dict[str, Any] = {}

    try:
        if probe_id == "verify_context":
            from tools.windows import do_list_windows, find_matching_window
            windows = do_list_windows()
            match = find_matching_window(target or window_title or "", windows)
            applied = match.get("window") is not None
            detail = {"matched": applied, "window": match.get("window")}

        elif probe_id == "rescan":
            from detection.discovery.resolver import resolve_target
            detail = resolve_target(
                hints=hints or ([target] if target else []),
                window_title=window_title,
                backend=params.get("backend"),
            )
            applied = detail.get("found", False)

        elif probe_id == "list_modals":
            from tools.windows import do_list_windows
            detail = {"windows": do_list_windows()[:10]}
            applied = True

        elif probe_id == "expand_menu":
            from detection.backends.uia_backend import get_uia_backend
            backend = get_uia_backend()
            result = backend.expand_element(name=target, role="MenuItem", window_title=window_title)
            if not result.get("success"):
                result = backend.invoke_element_by_name(target, role="MenuItem", window_title=window_title)
            applied = result.get("success", False)
            detail = result

        elif probe_id == "switch_tab":
            from detection.backends.uia_backend import get_uia_backend
            result = get_uia_backend().invoke_element_by_name(target, role="TabItem", window_title=window_title)
            applied = result.get("success", False)
            detail = result

        elif probe_id == "expand_tree":
            from detection.backends.uia_backend import get_uia_backend
            result = get_uia_backend().expand_element(name=target, role="TreeItem", window_title=window_title)
            applied = result.get("success", False)
            detail = result

        elif probe_id == "scroll_panel":
            from tools.input_tools import do_send_keys
            do_send_keys("{PGDN}")
            applied = True
            detail = {"keys": "{PGDN}"}

        elif probe_id == "access_key":
            from tools.input_tools import do_send_keys
            keys = params.get("keys") or target
            do_send_keys(keys)
            applied = True
            detail = {"keys": keys}

        elif probe_id == "dismiss_overlay":
            from tools.input_tools import do_send_keys
            from tools.highlight import clear_highlight
            do_send_keys("{ESC}")
            clear_highlight()
            applied = True
            detail = {"keys": "{ESC}"}

        elif probe_id == "find_by_template":
            from tools.template_match import find_by_template
            detail = find_by_template(
                params.get("image_path") or target,
                window_title=window_title,
                threshold=params.get("threshold", 0.75),
            )
            applied = detail.get("found", False)

        else:
            error = f"unknown probe: {probe_id}"

    except Exception as exc:
        error = str(exc)
        applied = False

    changed = False
    try:
        from tools.screenshot import wait_for_change
        wf = wait_for_change(timeout=2.0, threshold=0.005)
        changed = wf.get("changed", False)
    except Exception:
        pass

    after_obs = observe_ui(window_title=window_title, hints=hints)
    after_fp = after_obs.get("fingerprint", "")
    fingerprint_changed = bool(before_fp and after_fp and before_fp != after_fp)

    return {
        "applied": applied,
        "probe_id": probe_id,
        "target": target,
        "detail": detail,
        "error": error,
        "ui_changed": changed,
        "fingerprint_changed": fingerprint_changed,
        "observation": after_obs,
    }
