"""CPU frequency control module."""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from typing import List, Optional

from src.core.sensors import Capability


class CPUController:
    """Controls CPU frequency scaling limits."""

    CPU_PATH = "/sys/devices/system/cpu"
    FREQ_PRESETS = {
        "ultra_low": 1500000,
        "low": 2000000,
        "eco": 2500000,
        "cool": 3000000,
        "balanced": 3500000,
        "performance": 4000000,
        "high": 4500000,
        "max": 5263000,
    }

    def __init__(self):
        self.num_cores = self._count_cores()
        self.hw_max_freq = self._get_hw_max_freq()
        self.hw_min_freq = self._get_hw_min_freq()
        self.capability = self._detect_capability()
        self.last_error = ""

    def _detect_capability(self) -> Capability:
        if not os.path.exists(f"{self.CPU_PATH}/cpu0/cpufreq/scaling_max_freq"):
            return Capability(False, "CPU frequency scaling interface unavailable")
        if not shutil.which("sudo"):
            return Capability(False, "sudo not installed")
        return Capability(True)

    def _count_cores(self) -> int:
        return len(glob.glob(f"{self.CPU_PATH}/cpu[0-9]*"))

    def _get_hw_max_freq(self) -> int:
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/cpuinfo_max_freq", "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return 5263000

    def _get_hw_min_freq(self) -> int:
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/cpuinfo_min_freq", "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return 400000

    def get_current_freq(self, core: int = 0) -> int:
        try:
            with open(f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_cur_freq", "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return 0

    def get_max_freq(self, core: int = 0) -> int:
        try:
            with open(f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_max_freq", "r", encoding="utf-8") as handle:
                return int(handle.read().strip())
        except (OSError, ValueError):
            return self.hw_max_freq

    def get_all_core_freqs(self) -> List[int]:
        return [self.get_current_freq(index) for index in range(self.num_cores)]

    def get_governor(self) -> str:
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/scaling_governor", "r", encoding="utf-8") as handle:
                return handle.read().strip()
        except OSError:
            return "unknown"

    def get_available_governors(self) -> List[str]:
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/scaling_available_governors", "r", encoding="utf-8") as handle:
                return handle.read().strip().split()
        except OSError:
            return []

    def _write_with_sudo(self, path: str, value: str) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                ["sudo", "tee", path],
                input=value.encode(),
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            self.last_error = str(exc)
            return False, self.last_error

        if result.returncode != 0:
            self.last_error = (result.stderr or result.stdout or "").strip() or f"tee failed for {path}"
            return False, self.last_error
        self.last_error = ""
        return True, ""

    def set_max_freq(self, freq_khz: int, cores: Optional[List[int]] = None) -> tuple[bool, str]:
        if not self.capability.available:
            self.last_error = self.capability.reason
            return False, self.last_error

        freq_khz = max(self.hw_min_freq, min(freq_khz, self.hw_max_freq))
        targets = cores if cores is not None else list(range(self.num_cores))
        for core in targets:
            path = f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_max_freq"
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(str(freq_khz))
            except PermissionError:
                success, message = self._write_with_sudo(path, str(freq_khz))
                if not success:
                    return False, message
            except OSError as exc:
                self.last_error = str(exc)
                return False, self.last_error

        return True, "CPU frequency limit updated"

    def set_max_freq_all(self, freq_khz: int) -> tuple[bool, str]:
        return self.set_max_freq(freq_khz)

    def set_governor(self, governor: str) -> tuple[bool, str]:
        if governor not in self.get_available_governors():
            return False, f"Governor not available: {governor}"
        for core in range(self.num_cores):
            path = f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_governor"
            success, message = self._write_with_sudo(path, governor)
            if not success:
                return False, message
        return True, "CPU governor updated"

    def set_preset(self, preset_name: str) -> tuple[bool, str]:
        freq = self.FREQ_PRESETS.get(preset_name)
        if freq is None:
            return False, f"Unknown CPU preset: {preset_name}"
        return self.set_max_freq_all(freq)

    @staticmethod
    def freq_to_ghz(freq_khz: int) -> float:
        return freq_khz / 1000000.0

    @staticmethod
    def ghz_to_freq(ghz: float) -> int:
        return int(ghz * 1000000)
