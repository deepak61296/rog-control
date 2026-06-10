"""Fan and ASUS profile control backend."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from typing import List, Tuple

from src.core.process import run_command
from src.core.sensors import Capability

logger = logging.getLogger(__name__)


@dataclass
class FanCurve:
    """Predefined fan curve definition."""

    points: List[Tuple[int, int]]

    def to_asusctl_format(self) -> str:
        return ",".join(f"{temp}c:{percent}%" for temp, percent in self.points)


class FanController:
    """Controls ASUS fan profiles through asusctl."""

    FAN_CURVES = {
        "aggressive": FanCurve([(30, 50), (40, 60), (50, 70), (60, 80), (70, 90), (80, 95), (90, 100), (100, 100)]),
        "max": FanCurve([(30, 100), (40, 100), (50, 100), (60, 100), (70, 100), (80, 100), (90, 100), (100, 100)]),
    }
    PROFILES = ["Performance", "Balanced", "Quiet"]

    def __init__(self):
        self.asusctl_path = shutil.which("asusctl")
        self.capability = Capability(self.asusctl_path is not None, "" if self.asusctl_path else "asusctl not installed")
        self.last_error = ""

    def _run_asusctl(self, args: list[str]) -> tuple[bool, str]:
        if not self.capability.available or not self.asusctl_path:
            self.last_error = self.capability.reason
            return False, self.last_error

        success, output = run_command(
            [self.asusctl_path, *args],
            timeout=10,
        )
        if not success:
            self.last_error = output
            return False, self.last_error

        self.last_error = ""
        return True, output.strip()

    def get_profile(self) -> tuple[str | None, str]:
        success, output = self._run_asusctl(["profile", "-p"])
        if not success:
            return None, output

        for line in output.splitlines():
            if "Active profile" not in line:
                continue
            for profile in self.PROFILES:
                if profile in line:
                    return profile, ""
        return None, "Unable to parse active ASUS profile"

    def get_fan_curve_enabled(self) -> tuple[bool | None, str]:
        success, output = self._run_asusctl(["fan-curve", "-g"])
        if not success:
            return None, output
        return "enabled: true" in output.lower(), ""

    def set_profile(self, profile: str) -> tuple[bool, str]:
        if profile not in self.PROFILES:
            return False, f"Unsupported profile: {profile}"
        success, output = self._run_asusctl(["profile", "-P", profile])
        return success, "Fan profile updated" if success else output

    def apply_profile_behavior(self, profile: str) -> tuple[bool, str]:
        """Apply a profile with the app's expected fan behavior."""
        success, message = self.set_profile(profile)
        if not success:
            return False, message

        if profile == "Performance":
            success, message = self.set_max_fans(profile)
            if success:
                return True, "Performance profile applied with max fan curve"
            return False, message

        success, message = self.enable_custom_curves(profile, False)
        if success:
            return True, f"{profile} profile applied with firmware fan control"
        return False, message

    def set_fan_curve(self, curve: FanCurve, fan: str = "cpu", profile: str = "Performance") -> tuple[bool, str]:
        success, output = self._run_asusctl(["fan-curve", "-m", profile, "-f", fan, "-D", curve.to_asusctl_format()])
        return success, "Fan curve updated" if success else output

    def set_fan_curve_preset(self, preset: str, profile: str = "Performance") -> tuple[bool, str]:
        curve = self.FAN_CURVES.get(preset)
        if curve is None:
            return False, f"Unknown fan curve preset: {preset}"

        success_cpu, cpu_msg = self.set_fan_curve(curve, "cpu", profile)
        success_gpu, gpu_msg = self.set_fan_curve(curve, "gpu", profile)
        if success_cpu and success_gpu:
            return True, "Fan curve preset applied"
        return False, cpu_msg if not success_cpu else gpu_msg

    def enable_custom_curves(self, profile: str = "Performance", enable: bool = True) -> tuple[bool, str]:
        success, output = self._run_asusctl(["fan-curve", "-m", profile, "-e", str(enable).lower()])
        return success, "Custom fan curves enabled" if success else output

    def reset_fan_curve(self, profile: str = "Performance") -> tuple[bool, str]:
        success, output = self._run_asusctl(["fan-curve", "-m", profile, "-d"])
        return success, "Fan curves reset" if success else output

    def set_max_fans(self, profile: str = "Performance") -> tuple[bool, str]:
        success, output = self.set_fan_curve_preset("max", profile)
        if not success:
            return False, output
        return self.enable_custom_curves(profile, True)
