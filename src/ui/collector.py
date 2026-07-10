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
from src.core.power import PowerController
from src.core.sensors import SensorReader
from src.ui.state import AppState

logger = logging.getLogger(__name__)

HISTORY_LENGTH = 240


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

    @staticmethod
    def _append_history(history: list[float], value: float) -> list[float]:
        return (history + [value])[-HISTORY_LENGTH:]

    def _collect_sensors(self) -> None:
        while self._running.is_set():
            try:
                snapshot = self.sensors.get_snapshot()
                with self.lock:
                    self.state.snapshot = snapshot
                    if snapshot.cpu.temp_c is not None:
                        self.state.cpu_temp_history = self._append_history(self.state.cpu_temp_history, snapshot.cpu.temp_c)
                    if snapshot.cpu.util_percent is not None:
                        self.state.cpu_util_history = self._append_history(self.state.cpu_util_history, snapshot.cpu.util_percent)
                    if snapshot.nvidia_gpu.temp_c is not None:
                        self.state.gpu_temp_history = self._append_history(self.state.gpu_temp_history, snapshot.nvidia_gpu.temp_c)
                    if snapshot.nvidia_gpu.util_percent is not None:
                        self.state.gpu_util_history = self._append_history(self.state.gpu_util_history, float(snapshot.nvidia_gpu.util_percent))
                    if snapshot.nvidia_gpu.vram_used_mb is not None and snapshot.nvidia_gpu.vram_total_mb:
                        vram_pct = (snapshot.nvidia_gpu.vram_used_mb / snapshot.nvidia_gpu.vram_total_mb) * 100.0
                        self.state.vram_util_history = self._append_history(self.state.vram_util_history, vram_pct)
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
        """Return a safe view of the current state for the render thread.

        Background threads publish whole new SystemSnapshot/PowerInfo objects
        under the lock and never mutate them afterwards, so sharing those
        references is safe; only the mutable history/error lists are copied.
        """
        with self.lock:
            return AppState(
                snapshot=self.state.snapshot,
                power_info=self.state.power_info,
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
                cpu_util_history=list(self.state.cpu_util_history),
                gpu_temp_history=list(self.state.gpu_temp_history),
                gpu_util_history=list(self.state.gpu_util_history),
                vram_util_history=list(self.state.vram_util_history),
                errors=list(self.state.errors),
            )
