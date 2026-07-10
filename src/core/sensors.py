"""Hardware sensor readers and capability-aware telemetry snapshots."""

from __future__ import annotations

import logging
import os
import glob
import shutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core.process import run_command

logger = logging.getLogger(__name__)


def parse_proc_stat(text: str) -> Dict[str, tuple[int, int]]:
    """Parse /proc/stat into {label: (idle_ticks, total_ticks)} for cpu lines."""
    stats: Dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        parts = line.split()
        if not parts or not parts[0].startswith("cpu"):
            continue
        try:
            values = [int(part) for part in parts[1:]]
        except ValueError:
            continue
        if len(values) < 5:
            continue
        idle = values[3] + values[4]  # idle + iowait
        stats[parts[0]] = (idle, sum(values))
    return stats


def utilization_percent(current: tuple[int, int], last: tuple[int, int]) -> Optional[float]:
    """CPU busy percentage between two (idle, total) tick samples."""
    idle_delta = current[0] - last[0]
    total_delta = current[1] - last[1]
    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))


def parse_meminfo(text: str) -> "MemoryStats":
    """Parse /proc/meminfo (values in kB) into MemoryStats."""
    fields: Dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                fields[parts[0][:-1]] = int(parts[1])
            except ValueError:
                continue

    total = fields.get("MemTotal")
    available = fields.get("MemAvailable")
    swap_total = fields.get("SwapTotal")
    swap_free = fields.get("SwapFree")
    used = total - available if total is not None and available is not None else None
    swap_used = swap_total - swap_free if swap_total is not None and swap_free is not None else None
    return MemoryStats(
        total_mb=total // 1024 if total is not None else None,
        used_mb=used // 1024 if used is not None else None,
        available_mb=available // 1024 if available is not None else None,
        swap_total_mb=swap_total // 1024 if swap_total is not None else None,
        swap_used_mb=swap_used // 1024 if swap_used is not None else None,
    )


@dataclass
class Capability:
    """Runtime capability state for a backend or hardware path."""

    available: bool
    reason: str = ""


@dataclass
class CPUStats:
    temp_c: Optional[float] = None
    current_freq_mhz: Optional[int] = None
    max_freq_mhz: Optional[int] = None
    governor: Optional[str] = None
    util_percent: Optional[float] = None
    per_core_util: Optional[List[float]] = None
    per_core_freq_mhz: Optional[List[int]] = None


@dataclass
class MemoryStats:
    total_mb: Optional[int] = None
    used_mb: Optional[int] = None
    available_mb: Optional[int] = None
    swap_total_mb: Optional[int] = None
    swap_used_mb: Optional[int] = None


@dataclass
class AMDGPUStats:
    temp_c: Optional[float] = None
    clock_mhz: Optional[int] = None
    power_w: Optional[float] = None
    busy_percent: Optional[int] = None


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
    memory: MemoryStats = field(default_factory=MemoryStats)
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
        self._last_cpu_stat: Dict[str, tuple[int, int]] = {}
        self._num_cores = len(glob.glob("/sys/devices/system/cpu/cpu[0-9]*"))
        self.gpu_name = self._query_gpu_name()

    def _query_gpu_name(self) -> Optional[str]:
        if not self._nvidia_smi:
            return None
        success, output = run_command(
            [self._nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            env={**os.environ, "LC_ALL": "C"},
        )
        if not success or not output.strip():
            return None
        return output.strip().splitlines()[0].strip()

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

    def read_cpu_temp(self) -> Optional[float]:
        """Current CPU package temperature in °C, if the k10temp hwmon exists."""
        return self._read_hwmon_temp("k10temp")

    def _read_cpu_usage(self) -> tuple[Optional[float], Optional[List[float]]]:
        """Aggregate and per-core CPU utilization since the previous sample."""
        try:
            with open("/proc/stat", "r", encoding="utf-8") as handle:
                stats = parse_proc_stat(handle.read())
        except OSError:
            return None, None

        last = self._last_cpu_stat
        self._last_cpu_stat = stats

        total = None
        if "cpu" in stats and "cpu" in last:
            total = utilization_percent(stats["cpu"], last["cpu"])

        per_core: List[float] = []
        for index in range(self._num_cores):
            label = f"cpu{index}"
            if label in stats and label in last:
                value = utilization_percent(stats[label], last[label])
                per_core.append(value if value is not None else 0.0)
        return total, per_core or None

    def _read_core_freqs(self) -> Optional[List[int]]:
        freqs: List[int] = []
        for index in range(self._num_cores):
            value = self._read_int(f"/sys/devices/system/cpu/cpu{index}/cpufreq/scaling_cur_freq")
            freqs.append(value // 1000 if value is not None else 0)
        return freqs or None

    def _read_cpu(self, snapshot: SystemSnapshot) -> None:
        base = "/sys/devices/system/cpu/cpu0/cpufreq"
        current = self._read_int(os.path.join(base, "scaling_cur_freq"))
        maximum = self._read_int(os.path.join(base, "scaling_max_freq"))
        governor = self._read_sysfs(os.path.join(base, "scaling_governor"))
        util, per_core = self._read_cpu_usage()
        snapshot.cpu = CPUStats(
            temp_c=self._read_hwmon_temp("k10temp"),
            current_freq_mhz=current // 1000 if current is not None else None,
            max_freq_mhz=maximum // 1000 if maximum is not None else None,
            governor=governor,
            util_percent=util,
            per_core_util=per_core,
            per_core_freq_mhz=self._read_core_freqs(),
        )

    def _read_memory(self, snapshot: SystemSnapshot) -> None:
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                snapshot.memory = parse_meminfo(handle.read())
        except OSError:
            snapshot.memory = MemoryStats()

    def _read_amd_gpu(self, snapshot: SystemSnapshot) -> None:
        base = self._hwmon_paths.get("amdgpu")
        if not base:
            return

        temp_raw = self._read_int(os.path.join(base, "temp1_input"))
        clock_raw = self._read_int(os.path.join(base, "freq1_input"))
        power_raw = self._read_int(os.path.join(base, "power1_average"))
        busy = self._read_int(os.path.join(base, "device", "gpu_busy_percent"))
        snapshot.amd_gpu = AMDGPUStats(
            temp_c=temp_raw / 1000.0 if temp_raw is not None else None,
            clock_mhz=clock_raw // 1_000_000 if clock_raw is not None else None,
            power_w=power_raw / 1_000_000.0 if power_raw is not None else None,
            busy_percent=busy,
        )

    def _read_nvidia_gpu(self, snapshot: SystemSnapshot) -> Capability:
        if not self._nvidia_smi:
            return Capability(False, "nvidia-smi not installed")

        success, output = run_command(
            [
                self._nvidia_smi,
                "--query-gpu=temperature.gpu,power.draw,clocks.gr,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            env={**os.environ, "LC_ALL": "C"},
        )
        if not success:
            return Capability(False, f"NVIDIA telemetry unavailable: {output.strip() or 'unknown error'}")

        line = output.strip().splitlines()[0] if output.strip() else ""
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            return Capability(False, f"Unexpected nvidia-smi output: {line}")

        def safe_float(val: str) -> float | None:
            try:
                return float(val)
            except ValueError:
                return None

        def safe_int(val: str) -> int | None:
            try:
                return int(val)
            except ValueError:
                return None

        snapshot.nvidia_gpu = NvidiaGPUStats(
            temp_c=safe_float(parts[0]),
            power_w=safe_float(parts[1]),
            clock_mhz=safe_int(parts[2]),
            util_percent=safe_int(parts[3]),
            vram_used_mb=safe_int(parts[4]),
            vram_total_mb=safe_int(parts[5]),
        )

        return Capability(True)

    def _read_cooling(self, snapshot: SystemSnapshot) -> None:
        base = self._hwmon_paths.get("asus")
        if not base:
            paths = glob.glob("/sys/devices/platform/asus-nb-wmi/hwmon/hwmon*")
            if paths:
                base = paths[0]
            else:
                return

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
        # hwmon paths are detected once in __init__ — they do not change at runtime

        snapshot.capabilities["amd_hwmon"] = Capability(
            "amdgpu" in self._hwmon_paths,
            "" if "amdgpu" in self._hwmon_paths else "AMD GPU hwmon not detected",
        )
        asus_paths = glob.glob("/sys/devices/platform/asus-nb-wmi/hwmon/hwmon*")
        snapshot.capabilities["fan_hwmon"] = Capability(
            "asus" in self._hwmon_paths or len(asus_paths) > 0,
            "" if ("asus" in self._hwmon_paths or len(asus_paths) > 0) else "ASUS fan hwmon not detected",
        )
        snapshot.capabilities["cpu_hwmon"] = Capability(
            "k10temp" in self._hwmon_paths,
            "" if "k10temp" in self._hwmon_paths else "CPU temperature hwmon not detected",
        )

        self._read_cpu(snapshot)
        self._read_memory(snapshot)
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
