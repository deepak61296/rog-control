"""Typed control actions for the Textual UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CapabilityName = str


@dataclass(frozen=True)
class ControlAction:
    """A user-triggered hardware control action."""

    id: str
    panel: str
    key: str
    label: str
    description: str
    kind: str
    payload: Mapping[str, Any]
    capabilities: tuple[CapabilityName, ...]
    confirmation: str | None = None


def execute_control_action(action: ControlAction, collector) -> tuple[bool, str]:
    """Execute one control action against the backend collector."""

    if action.kind == "cpu_freq":
        return collector.cpu.set_max_freq_all(int(action.payload["freq"]))

    if action.kind == "power_preset":
        return collector.power.set_preset(str(action.payload["preset"]))

    if action.kind == "fan_profile":
        return collector.fans.apply_profile_behavior(str(action.payload["profile"]))

    if action.kind == "fan_curve":
        profile = _target_fan_profile(collector)
        success, message = collector.fans.set_fan_curve_preset(str(action.payload["preset"]), profile)
        if success:
            success, message = collector.fans.enable_custom_curves(profile, enable=True)
        return success, message

    if action.kind == "fan_reset":
        profile = _target_fan_profile(collector)
        success, message = collector.fans.reset_fan_curve(profile)
        if success:
            success, message = collector.fans.enable_custom_curves(profile, enable=False)
        return success, message

    if action.kind == "quick_preset":
        return _execute_quick_preset(action, collector)

    return False, f"Unknown action: {action.kind}"


def _execute_quick_preset(action: ControlAction, collector) -> tuple[bool, str]:
    name = str(action.payload["name"])
    freq = int(action.payload["freq"])
    power_preset = str(action.payload["power"])
    fan_profile = str(action.payload["fan_profile"])
    fan_curve = str(action.payload["fan_curve"])

    steps = [
        ("CPU frequency", lambda: collector.cpu.set_max_freq_all(freq)),
        ("Power preset", lambda: collector.power.set_preset(power_preset)),
        ("Fan profile", lambda: collector.fans.set_profile(fan_profile)),
        ("Fan curve", lambda: collector.fans.set_fan_curve_preset(fan_curve, fan_profile)),
        ("Custom fan curves", lambda: collector.fans.enable_custom_curves(fan_profile, enable=True)),
    ]
    for step_name, step in steps:
        success, message = step()
        if not success:
            return False, f"{step_name}: {message}"
    return True, f"Applied preset: {name}"


def _target_fan_profile(collector) -> str:
    state = collector.current_state()
    if state.fan_profile in {"Performance", "Balanced", "Quiet"}:
        return str(state.fan_profile)
    return "Performance"
