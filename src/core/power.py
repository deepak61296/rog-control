"""RyzenAdj power management backend."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from typing import Optional

from src.core.process import run_command
from src.core.sensors import Capability

logger = logging.getLogger(__name__)


@dataclass
class PowerInfo:
    """Current AMD power limit telemetry."""

    stapm_limit: Optional[float] = None
    stapm_value: Optional[float] = None
    fast_limit: Optional[float] = None
    fast_value: Optional[float] = None
    slow_limit: Optional[float] = None
    slow_value: Optional[float] = None
    tctl_limit: Optional[float] = None
    tctl_value: Optional[float] = None
    vrm_current: Optional[float] = None
    vrm_current_limit: Optional[float] = None
    vrm_max_current: Optional[float] = None
    vrm_max_current_limit: Optional[float] = None


class PowerController:
    """Controls AMD Ryzen power management through ryzenadj."""

    POWER_PRESETS = {
        "silent": {"stapm": 15000, "fast": 20000, "slow": 15000, "tctl": 75},
        "eco": {"stapm": 25000, "fast": 35000, "slow": 25000, "tctl": 80},
        "cool": {"stapm": 35000, "fast": 45000, "slow": 35000, "tctl": 85},
        "balanced": {"stapm": 45000, "fast": 55000, "slow": 45000, "tctl": 90},
        "performance": {"stapm": 55000, "fast": 65000, "slow": 55000, "tctl": 95},
        "high": {"stapm": 65000, "fast": 75000, "slow": 65000, "tctl": 95},
        "max": {"stapm": 80000, "fast": 80000, "slow": 80000, "tctl": 100},
    }

    def __init__(self):
        self.ryzenadj_path = self._find_ryzenadj()
        self.capability = self._detect_capability()
        self.last_error = ""

    def _find_ryzenadj(self) -> str:
        path = shutil.which("ryzenadj")
        if path:
            return path
        for candidate in ("/usr/local/bin/ryzenadj", "/usr/bin/ryzenadj"):
            if os.path.exists(candidate):
                return candidate
        return "ryzenadj"

    def _detect_capability(self) -> Capability:
        if not shutil.which("sudo"):
            return Capability(False, "sudo not installed")
        if os.path.exists(self.ryzenadj_path):
            ryzenadj_available = True
        else:
            ryzenadj_available = shutil.which(self.ryzenadj_path) is not None

        if not ryzenadj_available:
            return Capability(False, "ryzenadj not installed")

        success, output = run_command(["sudo", "-n", "true"], timeout=2, start_new_session=False)
        if success:
            return Capability(True)

        reason = output or "passwordless sudo is not available"
        return Capability(False, f"RyzenAdj needs sudo: {reason}")

    def _run_ryzenadj(self, args: list[str]) -> tuple[bool, str]:
        if not self.capability.available:
            self.last_error = self.capability.reason
            return False, self.last_error

        success, output = run_command(
            ["sudo", "-n", self.ryzenadj_path, *args],
            timeout=10,
            start_new_session=False,
        )
        if not success:
            self.last_error = output
            return False, self.last_error

        self.last_error = ""
        return True, output.strip()

    def get_power_info(self) -> PowerInfo:
        info = PowerInfo()
        success, output = self._run_ryzenadj(["-i"])
        if not success:
            return info

        for line in output.splitlines():
            if "|" not in line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 3:
                continue
            name = parts[1]
            value_text = parts[2]
            try:
                value = float(value_text)
            except ValueError:
                continue

            if "STAPM LIMIT" in name:
                info.stapm_limit = value
            elif "STAPM VALUE" in name:
                info.stapm_value = value
            elif "PPT LIMIT FAST" in name:
                info.fast_limit = value
            elif "PPT VALUE FAST" in name:
                info.fast_value = value
            elif "PPT LIMIT SLOW" in name:
                info.slow_limit = value
            elif "PPT VALUE SLOW" in name:
                info.slow_value = value
            elif "THM LIMIT CORE" in name:
                info.tctl_limit = value
            elif "THM VALUE CORE" in name:
                info.tctl_value = value
            elif "TDC VALUE VDD" in name:
                info.vrm_current = value
            elif "TDC LIMIT VDD" in name:
                info.vrm_current_limit = value
            elif "EDC VALUE VDD" in name:
                info.vrm_max_current = value
            elif "EDC LIMIT VDD" in name:
                info.vrm_max_current_limit = value

        return info

    def set_preset(self, preset_name: str) -> tuple[bool, str]:
        preset = self.POWER_PRESETS.get(preset_name)
        if preset is None:
            return False, f"Unknown preset: {preset_name}"

        args = [
            f'--stapm-limit={preset["stapm"]}',
            f'--fast-limit={preset["fast"]}',
            f'--slow-limit={preset["slow"]}',
            f'--tctl-temp={preset["tctl"]}',
        ]
        success, output = self._run_ryzenadj(args)
        return success, "Power preset applied" if success else output

    def apply_custom(self, stapm: int, fast: int, slow: int, tctl: int = 95) -> tuple[bool, str]:
        args = [
            f"--stapm-limit={stapm}",
            f"--fast-limit={fast}",
            f"--slow-limit={slow}",
            f"--tctl-temp={tctl}",
        ]
        success, output = self._run_ryzenadj(args)
        return success, "Power settings applied" if success else output
