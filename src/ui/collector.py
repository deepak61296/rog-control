"""Background telemetry collector for ROG Control.

Runs sensor, power, and fan status collection in separate daemon threads,
writing results into a shared AppState with proper locking.
"""

from __future__ import annotations

import logging
import threading
import time

from src.core.cpu import CPUController
from src.core.fans import FanController
from src.core.power import PowerController, PowerInfo
from src.core.sensors import SensorReader, SystemSnapshot, CPUStats, AMDGPUStats, NvidiaGPUStats, CoolingStats, BatteryStats
from src.ui.state import AppState

logger = logging.getLogger(__name__)


class DataCollector:
    """Background telemetry collector."""

    def __init__(self, state):
        self.state = state
        self.sensors = SensorReader()
        self.cpu = CPUController()
        self.power = PowerController()
        self.fans = FanController()
        self.lock = threading.Lock()
        self._running = threading.Event()
        self._running.set()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self._running.set()
        self._threads = [
            threading.Thread(target=self._collect_sensors, daemon=True),
            threading.Thread(target=self._collect_power, daemon=True),
            threading.Thread(target=self._collect_fan_status, daemon=True),
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._running.clear()
        for thread in self._threads:
            thread.join(timeout=2.0)

    def request_stop(self) -> None:
        self._running.clear()

    def is_running(self) -> bool:
        return self._running.is_set()

    def _record_error(self, message: str) -> None:
        if not message:
            return
        with self.lock:
            self._record_error_unlocked(message)

    def _record_error_unlocked(self, message: str) -> None:
        if not message:
            return
        self.state.errors = [message, *[item for item in self.state.errors if item != message]][:5]

    def _collect_sensors(self) -> None:
        while self._running.is_set():
            try:
                snapshot = self.sensors.get_snapshot()
                with self.lock:
                    self.state.snapshot = snapshot
                    if snapshot.cpu.temp_c is not None:
                        self.state.cpu_temp_history = (self.state.cpu_temp_history + [snapshot.cpu.temp_c])[-32:]
                    if snapshot.cpu.util_percent is not None:
                        self.state.cpu_util_history = (self.state.cpu_util_history + [snapshot.cpu.util_percent])[-32:]
                    if snapshot.nvidia_gpu.util_percent is not None:
                        self.state.gpu_util_history = (self.state.gpu_util_history + [float(snapshot.nvidia_gpu.util_percent)])[-32:]
                    if snapshot.nvidia_gpu.vram_used_mb is not None and snapshot.nvidia_gpu.vram_total_mb:
                        vram_pct = (snapshot.nvidia_gpu.vram_used_mb / snapshot.nvidia_gpu.vram_total_mb) * 100.0
                        self.state.vram_util_history = (self.state.vram_util_history + [vram_pct])[-32:]
                    for message in snapshot.errors:
                        self._record_error_unlocked(message)
            except Exception as exc:
                logger.exception("Sensor polling failed")
                self._record_error(f"Sensor polling failed: {exc}")
            time.sleep(1.0)

    def _collect_power(self) -> None:
        while self._running.is_set():
            try:
                info = self.power.get_power_info()
                with self.lock:
                    self.state.power_info = info
                    if self.power.last_error:
                        self._record_error_unlocked(self.power.last_error)
            except Exception as exc:
                logger.exception("Power polling failed")
                self._record_error(f"Power polling failed: {exc}")
            time.sleep(2.0)

    def _collect_fan_status(self) -> None:
        while self._running.is_set():
            try:
                profile, profile_error = self.fans.get_profile()
                curve_enabled, curve_error = self.fans.get_fan_curve_enabled()
                with self.lock:
                    self.state.fan_profile = profile
                    self.state.custom_curve_enabled = curve_enabled
                    if profile_error:
                        self._record_error_unlocked(profile_error)
                    if curve_error:
                        self._record_error_unlocked(curve_error)
            except Exception as exc:
                logger.exception("Fan polling failed")
                self._record_error(f"Fan polling failed: {exc}")
            time.sleep(4.0)

    def update_message(self, message: str, style: str = "cyan") -> None:
        with self.lock:
            self.state.message = message
            self.state.message_style = style
            self.state.message_time = time.time()
            if style == "red":
                self._record_error_unlocked(message)

    def current_state(self):
        """Return a safe copy of the current state for the render thread.

        Constructs new SystemSnapshot and PowerInfo from primitive fields
        to prevent the render thread from seeing partially-updated data
        while background threads are mutating the live state.
        """
        with self.lock:
            old = self.state.snapshot
            snapshot = SystemSnapshot(
                cpu=CPUStats(
                    temp_c=old.cpu.temp_c,
                    current_freq_mhz=old.cpu.current_freq_mhz,
                    max_freq_mhz=old.cpu.max_freq_mhz,
                    governor=old.cpu.governor,
                    util_percent=old.cpu.util_percent,
                ),
                amd_gpu=AMDGPUStats(
                    temp_c=old.amd_gpu.temp_c,
                    clock_mhz=old.amd_gpu.clock_mhz,
                    power_w=old.amd_gpu.power_w,
                ),
                nvidia_gpu=NvidiaGPUStats(
                    temp_c=old.nvidia_gpu.temp_c,
                    power_w=old.nvidia_gpu.power_w,
                    clock_mhz=old.nvidia_gpu.clock_mhz,
                    util_percent=old.nvidia_gpu.util_percent,
                    vram_used_mb=old.nvidia_gpu.vram_used_mb,
                    vram_total_mb=old.nvidia_gpu.vram_total_mb,
                ),
                cooling=CoolingStats(
                    cpu_fan_rpm=old.cooling.cpu_fan_rpm,
                    gpu_fan_rpm=old.cooling.gpu_fan_rpm,
                ),
                battery=BatteryStats(
                    percent=old.battery.percent,
                    power_w=old.battery.power_w,
                    status=old.battery.status,
                ),
                nvme_temp_c=old.nvme_temp_c,
                capabilities=dict(old.capabilities),
                errors=list(old.errors),
            )
            old_power = self.state.power_info
            power_info = PowerInfo(
                stapm_limit=old_power.stapm_limit,
                stapm_value=old_power.stapm_value,
                fast_limit=old_power.fast_limit,
                fast_value=old_power.fast_value,
                slow_limit=old_power.slow_limit,
                slow_value=old_power.slow_value,
                tctl_limit=old_power.tctl_limit,
                tctl_value=old_power.tctl_value,
                vrm_current=old_power.vrm_current,
                vrm_current_limit=old_power.vrm_current_limit,
                vrm_max_current=old_power.vrm_max_current,
                vrm_max_current_limit=old_power.vrm_max_current_limit,
            )
            return AppState(
                snapshot=snapshot,
                power_info=power_info,
                fan_profile=self.state.fan_profile,
                custom_curve_enabled=self.state.custom_curve_enabled,
                cpu_capability=self.cpu.capability,
                power_capability=self.power.capability,
                fan_capability=self.fans.capability,
                cpu_error=self.cpu.last_error,
                power_error=self.power.last_error,
                fan_error=self.fans.last_error,
                message=self.state.message,
                message_style=self.state.message_style,
                message_time=self.state.message_time,
                active_menu=self.state.active_menu,
                pending_confirm=self.state.pending_confirm,
                cpu_temp_history=list(self.state.cpu_temp_history),
                amd_gpu_temp_history=list(self.state.amd_gpu_temp_history),
                cpu_util_history=list(self.state.cpu_util_history),
                gpu_util_history=list(self.state.gpu_util_history),
                vram_util_history=list(self.state.vram_util_history),
                errors=list(self.state.errors),
            )
