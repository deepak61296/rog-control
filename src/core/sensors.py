"""Hardware sensor readers and capability-aware telemetry snapshots."""

from __future__ import annotations

import os
import glob
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Capability:
    """Runtime capability state for a backend or hardware path."""

    available: bool
    reason: str = ""
    last_error: str = ""


@dataclass
class CPUStats:
    temp_c: Optional[float] = None
    current_freq_mhz: Optional[int] = None
    max_freq_mhz: Optional[int] = None
    governor: Optional[str] = None


@dataclass
class AMDGPUStats:
    temp_c: Optional[float] = None
    clock_mhz: Optional[int] = None
    power_w: Optional[float] = None


@dataclass
class NvidiaGPUStats:
    temp_c: Optional[float] = None
    power_w: Optional[float] = None
    clock_mhz: Optional[int] = None
    util_percent: Optional[int] = None
    vram_used_mb: Optional[int] = None
    vram_total_mb: Optional[int] = None


@dataclass
class CoolingStats:
    cpu_fan_rpm: Optional[int] = None
    gpu_fan_rpm: Optional[int] = None


@dataclass
class BatteryStats:
    percent: Optional[int] = None
    power_w: Optional[float] = None
    status: Optional[str] = None


@dataclass
class SystemSnapshot:
    """Current telemetry snapshot for the UI."""

    cpu: CPUStats = field(default_factory=CPUStats)
    amd_gpu: AMDGPUStats = field(default_factory=AMDGPUStats)
    nvidia_gpu: NvidiaGPUStats = field(default_factory=NvidiaGPUStats)
    cooling: CoolingStats = field(default_factory=CoolingStats)
    battery: BatteryStats = field(default_factory=BatteryStats)
    nvme_temp_c: Optional[float] = None
    capabilities: Dict[str, Capability] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class SensorReader:
    """Read hardware telemetry from sysfs and command backends."""

    def __init__(self):
        self._hwmon_paths = self._detect_hwmon_paths()
        self._nvidia_smi = shutil.which("nvidia-smi")
        self._hwmon_paths_valid = True

    def _detect_hwmon_paths(self) -> Dict[str, str]:
        paths: Dict[str, str] = {}
        for hwmon_dir in glob.glob("/sys/class/hwmon/hwmon*"):
            name_file = os.path.join(hwmon_dir, "name")
            if not os.path.exists(name_file):
                continue
            try:
                with open(name_file, "r", encoding="utf-8") as handle:
                    name = handle.read().strip()
            except OSError:
                continue
            paths[name] = hwmon_dir
        return paths

    def _read_sysfs(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        except (OSError, PermissionError):
            return None

    def _read_int(self, path: str) -> Optional[int]:
        value = self._read_sysfs(path)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _read_hwmon_temp(self, chip: str, sensor: str = "temp1_input") -> Optional[float]:
        base = self._hwmon_paths.get(chip)
        if not base:
            return None
        value = self._read_int(os.path.join(base, sensor))
        if value is None:
            return None
        return value / 1000.0

    def _read_optional_command(self, cmd: list[str], timeout: int = 5) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return False, "command not found"
        except subprocess.TimeoutExpired:
            return False, "command timed out"

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            cleaned = output.strip() or f"exit code {result.returncode}"
            return False, cleaned
        return True, output

    def _read_cpu(self, snapshot: SystemSnapshot) -> None:
        base = "/sys/devices/system/cpu/cpu0/cpufreq"
        current = self._read_int(os.path.join(base, "scaling_cur_freq"))
        maximum = self._read_int(os.path.join(base, "scaling_max_freq"))
        governor = self._read_sysfs(os.path.join(base, "scaling_governor"))
        temp = self._read_hwmon_temp("k10temp")
        snapshot.cpu = CPUStats(
            temp_c=temp,
            current_freq_mhz=current // 1000 if current is not None else None,
            max_freq_mhz=maximum // 1000 if maximum is not None else None,
            governor=governor,
        )
        # Mark hwmon paths as invalid if temp read fails (path might have changed)
        if temp is None and "k10temp" in self._hwmon_paths:
            self._hwmon_paths_valid = False

    def _read_amd_gpu(self, snapshot: SystemSnapshot) -> None:
        base = self._hwmon_paths.get("amdgpu")
        if not base:
            return

        temp_raw = self._read_int(os.path.join(base, "temp1_input"))
        clock_raw = self._read_int(os.path.join(base, "freq1_input"))
        power_raw = self._read_int(os.path.join(base, "power1_average"))
        snapshot.amd_gpu = AMDGPUStats(
            temp_c=temp_raw / 1000.0 if temp_raw is not None else None,
            clock_mhz=clock_raw // 1_000_000 if clock_raw is not None else None,
            power_w=power_raw / 1_000_000.0 if power_raw is not None else None,
        )

    def _read_nvidia_gpu(self, snapshot: SystemSnapshot) -> Capability:
        if not self._nvidia_smi:
            return Capability(False, "nvidia-smi not installed")

        success, output = self._read_optional_command(
            [
                self._nvidia_smi,
                "--query-gpu=temperature.gpu,power.draw,clocks.gr,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ]
        )
        if not success:
            return Capability(False, "NVIDIA telemetry unavailable", output)

        line = output.strip().splitlines()[0] if output.strip() else ""
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            return Capability(False, "Unexpected nvidia-smi output", line)

        try:
            snapshot.nvidia_gpu = NvidiaGPUStats(
                temp_c=float(parts[0]),
                power_w=float(parts[1]),
                clock_mhz=int(parts[2]),
                util_percent=int(parts[3]),
                vram_used_mb=int(parts[4]),
                vram_total_mb=int(parts[5]),
            )
        except ValueError as exc:
            return Capability(False, "Failed to parse nvidia-smi output", str(exc))

        return Capability(True)

    def _read_cooling(self, snapshot: SystemSnapshot) -> None:
        base = self._hwmon_paths.get("asus")
        if not base:
            base = "/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6"

        cpu_fan = self._read_int(os.path.join(base, "fan1_input"))
        gpu_fan = self._read_int(os.path.join(base, "fan2_input"))
        snapshot.cooling = CoolingStats(cpu_fan_rpm=cpu_fan, gpu_fan_rpm=gpu_fan)

    def _read_battery(self, snapshot: SystemSnapshot) -> Capability:
        base = "/sys/class/power_supply/BAT0"
        if not os.path.exists(base):
            return Capability(False, "Battery not detected")

        percent = self._read_int(os.path.join(base, "capacity"))
        power_raw = self._read_int(os.path.join(base, "power_now"))
        status = self._read_sysfs(os.path.join(base, "status"))
        snapshot.battery = BatteryStats(
            percent=percent,
            power_w=power_raw / 1_000_000.0 if power_raw is not None else None,
            status=status,
        )
        return Capability(True)

    def get_snapshot(self) -> SystemSnapshot:
        snapshot = SystemSnapshot()
        # Only re-detect hwmon paths if previous detection failed or on explicit refresh
        if not self._hwmon_paths_valid or not self._hwmon_paths:
            self._hwmon_paths = self._detect_hwmon_paths()
            self._hwmon_paths_valid = bool(self._hwmon_paths)

        snapshot.capabilities["amd_hwmon"] = Capability(
            "amdgpu" in self._hwmon_paths,
            "" if "amdgpu" in self._hwmon_paths else "AMD GPU hwmon not detected",
        )
        snapshot.capabilities["fan_hwmon"] = Capability(
            "asus" in self._hwmon_paths or os.path.exists("/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6"),
            "" if ("asus" in self._hwmon_paths or os.path.exists("/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6")) else "ASUS fan hwmon not detected",
        )
        snapshot.capabilities["cpu_hwmon"] = Capability(
            "k10temp" in self._hwmon_paths,
            "" if "k10temp" in self._hwmon_paths else "CPU temperature hwmon not detected",
        )

        self._read_cpu(snapshot)
        self._read_amd_gpu(snapshot)
        self._read_cooling(snapshot)
        snapshot.nvme_temp_c = self._read_hwmon_temp("nvme")
        snapshot.capabilities["battery"] = self._read_battery(snapshot)
        snapshot.capabilities["nvidia"] = self._read_nvidia_gpu(snapshot)

        if snapshot.cpu.temp_c is None and not snapshot.capabilities["cpu_hwmon"].available:
            snapshot.errors.append(snapshot.capabilities["cpu_hwmon"].reason)
        if (
            not snapshot.capabilities["amd_hwmon"].available
            and not snapshot.capabilities["nvidia"].available
        ):
            snapshot.errors.append("No GPU telemetry backend detected")

        return snapshot
