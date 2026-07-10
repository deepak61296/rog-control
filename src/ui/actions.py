"""Typed control actions for the Textual UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.profile import ProfileStore

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

def _save_profile(updates: dict[str, Any]) -> tuple[bool, str]:
    return ProfileStore().save_updates(updates)


def _with_save_warning(message: str, save_success: bool, save_message: str) -> str:
    if save_success:
        return message
    if "password is required" in save_message.lower():
        return f"{message}; not saved for reboot because sudo is not available"
    return f"{message}; not saved for reboot: {save_message}"


def execute_control_action(action: ControlAction, collector) -> tuple[bool, str]:
    """Execute one control action against the backend collector and save the state."""

    if action.kind == "cpu_freq":
        success, msg = collector.cpu.set_max_freq_all(int(action.payload["freq"]))
        if success:
            saved, save_msg = _save_profile({"cpu_freq": int(action.payload["freq"])})
            if not saved:
                return True, _with_save_warning(msg, saved, save_msg)
        return success, msg

    if action.kind == "power_preset":
        success, msg = collector.power.set_preset(str(action.payload["preset"]))
        if success:
            saved, save_msg = _save_profile({"power_preset": str(action.payload["preset"])})
            if not saved:
                return True, _with_save_warning(msg, saved, save_msg)
        return success, msg

    if action.kind == "fan_profile":
        profile = str(action.payload["profile"])
        success, msg = collector.fans.apply_profile_behavior(profile)
        if success:
            updates: dict[str, Any] = {"fan_profile": profile}
            if profile == "Performance":
                updates["fan_curve"] = "max"
            else:
                updates["fan_reset"] = True
            saved, save_msg = _save_profile(updates)
            if not saved:
                return True, _with_save_warning(msg, saved, save_msg)
        return success, msg

    if action.kind == "fan_curve":
        profile = _target_fan_profile(collector)
        success, message = collector.fans.set_fan_curve_preset(str(action.payload["preset"]), profile)
        if success:
            success, message = collector.fans.enable_custom_curves(profile, enable=True)
            if success:
                saved, save_msg = _save_profile({"fan_curve": str(action.payload["preset"]), "fan_profile": profile})
                if not saved:
                    return True, _with_save_warning(message, saved, save_msg)
        return success, message

    if action.kind == "fan_reset":
        profile = _target_fan_profile(collector)
        success, message = collector.fans.reset_fan_curve(profile)
        if success:
            success, message = collector.fans.enable_custom_curves(profile, enable=False)
            if success:
                saved, save_msg = _save_profile({"fan_reset": True, "fan_profile": profile})
                if not saved:
                    return True, _with_save_warning(message, saved, save_msg)
        return success, message

    if action.kind == "quick_preset":
        return _execute_quick_preset(action, collector)

    return False, f"Unknown action: {action.kind}"

def _execute_quick_preset(action: ControlAction, collector) -> tuple[bool, str]:
    name = str(action.payload["name"])
    freq = int(action.payload["freq"])
    power_preset = str(action.payload["power"])
    fan_profile = str(action.payload["fan_profile"])
    fan_mode = str(action.payload["fan_mode"])

    steps = [
        ("cpu_freq", "CPU frequency", freq, lambda: collector.cpu.set_max_freq_all(freq)),
        ("power_preset", "Power preset", power_preset, lambda: collector.power.set_preset(power_preset)),
        ("fan_profile", "Fan profile", fan_profile, lambda: collector.fans.set_profile(fan_profile)),
    ]
    if fan_mode == "firmware":
        steps.extend(
            [
                (None, "Fan curve reset", None, lambda: collector.fans.reset_fan_curve(fan_profile)),
                ("fan_reset", "Firmware fan control", True, lambda: collector.fans.enable_custom_curves(fan_profile, enable=False)),
            ]
        )
    elif fan_mode in {"aggressive", "max"}:
        steps.extend(
            [
                (None, "Fan curve", None, lambda: collector.fans.set_fan_curve_preset(fan_mode, fan_profile)),
                ("fan_curve", "Custom fan curves", fan_mode, lambda: collector.fans.enable_custom_curves(fan_profile, enable=True)),
            ]
        )
    else:
        return False, f"Unsupported quick fan mode: {fan_mode}"

    applied_updates = {}

    for config_key, step_name, config_val, step in steps:
        success, message = step()
        if config_key and success:
            applied_updates[config_key] = config_val

        if not success:
            if applied_updates:
                _save_profile(applied_updates)
            return False, f"{step_name}: {message}"

    saved, save_msg = _save_profile(applied_updates)
    if not saved:
        return True, _with_save_warning(f"Applied preset: {name}", saved, save_msg)
    return True, f"Applied preset: {name}"


def _target_fan_profile(collector) -> str:
    state = collector.current_state()
    if state.fan_profile in {"Performance", "Balanced", "Quiet"}:
        return str(state.fan_profile)
    return "Performance"
