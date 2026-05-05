"""Rich-based terminal application for ROG Control."""

from __future__ import annotations

import select
import sys
import termios
import threading
import time
import tty
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Optional

from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.core.cpu import CPUController
from src.core.fans import FanController
from src.core.power import PowerController, PowerInfo
from src.core.sensors import Capability, SystemSnapshot, SensorReader


@dataclass
class AppState:
    snapshot: SystemSnapshot = field(default_factory=SystemSnapshot)
    power_info: PowerInfo = field(default_factory=PowerInfo)
    fan_profile: Optional[str] = None
    custom_curve_enabled: Optional[bool] = None
    message: str = "Press h for help."
    message_style: str = "cyan"
    message_time: float = field(default_factory=time.time)
    active_menu: Optional[str] = None
    running: bool = True
    cpu_temp_history: list[float] = field(default_factory=list)
    amd_gpu_temp_history: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TerminalInput(AbstractContextManager["TerminalInput"]):
    """Read single keys without waiting for Enter."""

    def __init__(self):
        self._fd = sys.stdin.fileno()
        self._original = None

    def __enter__(self) -> "TerminalInput":
        self._original = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._original is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._original)

    def read_key(self, timeout: float = 0.1) -> Optional[str]:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        char = sys.stdin.read(1)
        if char == "\x1b":
            next_ready, _, _ = select.select([sys.stdin], [], [], 0.005)
            if next_ready:
                char += sys.stdin.read(2)
        return char


class DataCollector:
    """Background telemetry collector."""

    def __init__(self, state: AppState):
        self.state = state
        self.sensors = SensorReader()
        self.cpu = CPUController()
        self.power = PowerController()
        self.fans = FanController()
        self.lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self._threads = [
            threading.Thread(target=self._collect_sensors, daemon=True),
            threading.Thread(target=self._collect_power, daemon=True),
            threading.Thread(target=self._collect_fan_status, daemon=True),
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self.state.running = False
        for thread in self._threads:
            thread.join(timeout=0.2)

    def _record_error(self, message: str) -> None:
        if not message:
            return
        with self.lock:
            self.state.errors = [message, *[item for item in self.state.errors if item != message]][:5]

    def _collect_sensors(self) -> None:
        while self.state.running:
            snapshot = self.sensors.get_snapshot()
            with self.lock:
                self.state.snapshot = snapshot
                if snapshot.cpu.temp_c is not None:
                    self.state.cpu_temp_history = (self.state.cpu_temp_history + [snapshot.cpu.temp_c])[-32:]
                if snapshot.amd_gpu.temp_c is not None:
                    self.state.amd_gpu_temp_history = (self.state.amd_gpu_temp_history + [snapshot.amd_gpu.temp_c])[-32:]
                for message in snapshot.errors:
                    if message:
                        self.state.errors = [message, *[item for item in self.state.errors if item != message]][:5]
            time.sleep(1.0)

    def _collect_power(self) -> None:
        while self.state.running:
            info = self.power.get_power_info()
            with self.lock:
                self.state.power_info = info
                if self.power.last_error:
                    self.state.errors = [self.power.last_error, *[item for item in self.state.errors if item != self.power.last_error]][:5]
            time.sleep(2.0)

    def _collect_fan_status(self) -> None:
        while self.state.running:
            profile, profile_error = self.fans.get_profile()
            curve_enabled, curve_error = self.fans.get_fan_curve_enabled()
            with self.lock:
                self.state.fan_profile = profile
                self.state.custom_curve_enabled = curve_enabled
                if profile_error:
                    self.state.errors = [profile_error, *[item for item in self.state.errors if item != profile_error]][:5]
                if curve_error:
                    self.state.errors = [curve_error, *[item for item in self.state.errors if item != curve_error]][:5]
            time.sleep(4.0)

    def update_message(self, message: str, style: str = "cyan") -> None:
        with self.lock:
            self.state.message = message
            self.state.message_style = style
            self.state.message_time = time.time()

    def current_state(self) -> AppState:
        with self.lock:
            return AppState(
                snapshot=self.state.snapshot,
                power_info=self.state.power_info,
                fan_profile=self.state.fan_profile,
                custom_curve_enabled=self.state.custom_curve_enabled,
                message=self.state.message,
                message_style=self.state.message_style,
                message_time=self.state.message_time,
                active_menu=self.state.active_menu,
                running=self.state.running,
                cpu_temp_history=list(self.state.cpu_temp_history),
                amd_gpu_temp_history=list(self.state.amd_gpu_temp_history),
                errors=list(self.state.errors),
            )


def _sparkline(values: list[float], width: int = 12) -> str:
    if len(values) < 2:
        return " " * width
    chars = "▁▂▃▄▅▆▇█"
    recent = values[-width:]
    low = min(recent)
    high = max(recent)
    span = high - low or 1.0
    return "".join(chars[min(7, int(((value - low) / span) * 7))] for value in recent).rjust(width)


def _fmt_temp(value: Optional[float]) -> str:
    return f"{value:.1f} C" if value is not None else "Unavailable"


def _fmt_power(value: Optional[float]) -> str:
    return f"{value:.1f} W" if value is not None else "Unavailable"


def _fmt_freq(value: Optional[int]) -> str:
    return f"{value / 1000:.2f} GHz" if value is not None else "Unavailable"


def _fmt_rpm(value: Optional[int]) -> str:
    return f"{value} RPM" if value is not None else "Unavailable"


def _fmt_percent(value: Optional[int]) -> str:
    return f"{value}%" if value is not None else "Unavailable"


def _capability_badge(capability: Capability, label: str) -> Text:
    if capability.available:
        return Text(f"{label}: OK", style="bold green")
    return Text(f"{label}: {capability.reason}", style="bold yellow")


class RogControlApp:
    """Main Rich terminal application."""

    CPU_PRESETS = {
        "1": ("Silent cap", 2500000),
        "2": ("Cool cap", 3000000),
        "3": ("Balanced cap", 3500000),
        "4": ("Performance cap", 4000000),
        "5": ("High cap", 4500000),
        "6": ("Hardware max", 5263000),
    }
    POWER_PRESETS = {
        "1": ("Silent", "silent"),
        "2": ("Eco", "eco"),
        "3": ("Cool", "cool"),
        "4": ("Balanced", "balanced"),
        "5": ("Performance", "performance"),
        "6": ("High", "high"),
        "7": ("Maximum", "max"),
    }
    FAN_PROFILES = {"1": "Performance", "2": "Balanced", "3": "Quiet"}
    FAN_CURVES = {"1": "silent", "2": "quiet", "3": "balanced", "4": "aggressive", "5": "max"}
    QUICK_PRESETS = {
        "1": ("Quiet Work", 2500000, "silent", "Quiet", "quiet"),
        "2": ("Cool Daily", 3000000, "cool", "Balanced", "balanced"),
        "3": ("Balanced", 3500000, "balanced", "Balanced", "balanced"),
        "4": ("Heavy Load", 4500000, "performance", "Performance", "aggressive"),
    }

    def __init__(self):
        self.console = Console()
        self.state = AppState()
        self.collector = DataCollector(self.state)

    def run(self) -> int:
        self.collector.start()
        with TerminalInput() as keyboard, Live(self.render(), console=self.console, screen=True, auto_refresh=False) as live:
            while self.state.running:
                key = keyboard.read_key(timeout=0.15)
                if key:
                    self.handle_key(key)
                live.update(self.render(), refresh=True)
        self.collector.stop()
        return 0

    def handle_key(self, key: str) -> None:
        normalized = key.lower()
        if self.state.active_menu:
            self._handle_menu_input(normalized)
            return

        if normalized == "q":
            self.state.running = False
        elif normalized == "1":
            self.state.active_menu = "cpu"
        elif normalized == "2":
            self.state.active_menu = "power"
        elif normalized == "3":
            self.state.active_menu = "fan_profile"
        elif normalized == "4":
            self.state.active_menu = "fan_curve"
        elif normalized == "5":
            self.state.active_menu = "quick"
        elif normalized == "r":
            self.collector.update_message("Refresh loop is live; telemetry updates automatically.", "green")
        elif normalized == "h":
            self.state.active_menu = "help"

    def _handle_menu_input(self, key: str) -> None:
        if key in {"q", "\x1b", "b"}:
            self.state.active_menu = None
            return

        active = self.state.active_menu
        if active == "cpu":
            self._handle_cpu_menu(key)
        elif active == "power":
            self._handle_power_menu(key)
        elif active == "fan_profile":
            self._handle_fan_profile_menu(key)
        elif active == "fan_curve":
            self._handle_fan_curve_menu(key)
        elif active == "quick":
            self._handle_quick_preset_menu(key)
        elif active == "help":
            self.state.active_menu = None

    def _handle_cpu_menu(self, key: str) -> None:
        preset = self.CPU_PRESETS.get(key)
        if preset is None:
            return
        _, freq = preset
        success, message = self.collector.cpu.set_max_freq_all(freq)
        self.collector.update_message(message, "green" if success else "red")
        self.state.active_menu = None

    def _handle_power_menu(self, key: str) -> None:
        preset = self.POWER_PRESETS.get(key)
        if preset is None:
            return
        _, name = preset
        success, message = self.collector.power.set_preset(name)
        self.collector.update_message(message, "green" if success else "red")
        self.state.active_menu = None

    def _handle_fan_profile_menu(self, key: str) -> None:
        profile = self.FAN_PROFILES.get(key)
        if profile is None:
            return
        success, message = self.collector.fans.apply_profile_behavior(profile)
        self.collector.update_message(message, "green" if success else "red")
        self.state.active_menu = None

    def _handle_fan_curve_menu(self, key: str) -> None:
        if key == "d":
            success, message = self.collector.fans.reset_fan_curve()
            if success:
                success, message = self.collector.fans.enable_custom_curves(enable=False)
            self.collector.update_message(message, "green" if success else "red")
            self.state.active_menu = None
            return

        preset = self.FAN_CURVES.get(key)
        if preset is None:
            return
        success, message = self.collector.fans.set_fan_curve_preset(preset)
        if success:
            success, message = self.collector.fans.enable_custom_curves(enable=True)
        self.collector.update_message(message, "green" if success else "red")
        self.state.active_menu = None

    def _handle_quick_preset_menu(self, key: str) -> None:
        preset = self.QUICK_PRESETS.get(key)
        if preset is None:
            return
        _, freq, power_preset, fan_profile, curve_name = preset
        actions = [
            self.collector.cpu.set_max_freq_all(freq),
            self.collector.power.set_preset(power_preset),
            self.collector.fans.set_profile(fan_profile),
            self.collector.fans.set_fan_curve_preset(curve_name),
            self.collector.fans.enable_custom_curves(enable=True),
        ]
        failures = [message for success, message in actions if not success]
        if failures:
            self.collector.update_message(failures[0], "red")
        else:
            self.collector.update_message(f"Applied preset: {preset[0]}", "green")
        self.state.active_menu = None

    def render(self) -> RenderableType:
        width = self.console.size.width
        state = self.collector.current_state()
        if width < 90:
            return self._render_compact(state)

        header = self._render_header(state)
        rows = [
            Columns([self._render_cpu_panel(state), self._render_cooling_panel(state)], equal=True, expand=True),
            Columns([self._render_amd_gpu_panel(state), self._render_nvidia_panel(state)], equal=True, expand=True),
            Columns([self._render_power_panel(state), self._render_battery_panel(state)], equal=True, expand=True),
            self._render_footer(state),
        ]
        if state.active_menu:
            rows.append(self._render_menu(state))
        return Group(header, *rows)

    def _render_header(self, state: AppState) -> Panel:
        snapshot = state.snapshot
        badges = [
            _capability_badge(snapshot.capabilities.get("cpu_hwmon", Capability(False, "unknown")), "CPU"),
            _capability_badge(snapshot.capabilities.get("amd_hwmon", Capability(False, "unknown")), "AMD GPU"),
            _capability_badge(snapshot.capabilities.get("nvidia", Capability(False, "unknown")), "NVIDIA"),
            self._backend_badge(self.collector.power.capability, self.collector.power.last_error, "RyzenAdj"),
            self._backend_badge(self.collector.fans.capability, self.collector.fans.last_error, "ASUSCtl"),
        ]
        body = Columns(badges, expand=True)
        title = Text("ROG Control", style="bold cyan")
        subtitle = Text("Telemetry and thermal controls", style="dim")
        return Panel(Group(Align.center(title), Align.center(subtitle), body), border_style="cyan")

    def _metric_table(self, title: str, rows: list[tuple[str, str]]) -> Panel:
        table = Table.grid(expand=True)
        table.add_column(style="bold white", ratio=1)
        table.add_column(justify="right", ratio=1)
        for label, value in rows:
            table.add_row(label, value)
        return Panel(table, title=title, border_style="blue")

    def _render_cpu_panel(self, state: AppState) -> Panel:
        cpu = state.snapshot.cpu
        rows = [
            ("Temperature", _fmt_temp(cpu.temp_c)),
            ("Current", _fmt_freq(cpu.current_freq_mhz)),
            ("Limit", _fmt_freq(cpu.max_freq_mhz)),
            ("Governor", cpu.governor or "Unavailable"),
            ("Trend", _sparkline(state.cpu_temp_history)),
        ]
        return self._metric_table("CPU", rows)

    def _render_cooling_panel(self, state: AppState) -> Panel:
        cooling = state.snapshot.cooling
        fan_status = "Enabled" if state.custom_curve_enabled else "Disabled"
        if state.custom_curve_enabled is None:
            fan_status = "Unavailable"
        rows = [
            ("CPU Fan", _fmt_rpm(cooling.cpu_fan_rpm)),
            ("GPU Fan", _fmt_rpm(cooling.gpu_fan_rpm)),
            ("Profile", state.fan_profile or "Unavailable"),
            ("Custom Curve", fan_status),
            ("NVMe Temp", _fmt_temp(state.snapshot.nvme_temp_c)),
        ]
        capability = self.collector.fans.capability
        details = self.collector.fans.last_error or capability.reason
        panel = self._metric_table("Cooling", rows)
        if capability.available and not details:
            return panel
        return Panel(Group(panel.renderable, Text(details or "Cooling controls healthy", style="yellow")), title="Cooling", border_style="yellow")

    def _render_amd_gpu_panel(self, state: AppState) -> Panel:
        gpu = state.snapshot.amd_gpu
        capability = state.snapshot.capabilities.get("amd_hwmon", Capability(False, "AMD GPU telemetry unavailable"))
        rows = [
            ("Temperature", _fmt_temp(gpu.temp_c)),
            ("Clock", f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else "Unavailable"),
            ("Power", _fmt_power(gpu.power_w)),
            ("Trend", _sparkline(state.amd_gpu_temp_history)),
        ]
        panel = self._metric_table("AMD iGPU", rows)
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")), title="AMD iGPU", border_style="yellow")

    def _render_nvidia_panel(self, state: AppState) -> Panel:
        gpu = state.snapshot.nvidia_gpu
        capability = state.snapshot.capabilities.get("nvidia", Capability(False, "NVIDIA telemetry unavailable"))
        rows = [
            ("Temperature", _fmt_temp(gpu.temp_c)),
            ("Clock", f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else "Unavailable"),
            ("Power", _fmt_power(gpu.power_w)),
            ("Utilization", _fmt_percent(gpu.util_percent)),
            ("VRAM", f"{gpu.vram_used_mb}/{gpu.vram_total_mb} MB" if gpu.vram_used_mb is not None and gpu.vram_total_mb is not None else "Unavailable"),
        ]
        panel = self._metric_table("NVIDIA dGPU", rows)
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")), title="NVIDIA dGPU", border_style="yellow")

    def _render_power_panel(self, state: AppState) -> Panel:
        info = state.power_info
        rows = [
            ("STAPM", self._limit_value(info.stapm_value, info.stapm_limit)),
            ("Fast PPT", self._limit_value(info.fast_value, info.fast_limit)),
            ("Slow PPT", self._limit_value(info.slow_value, info.slow_limit)),
            ("Thermal", self._limit_value(info.tctl_value, info.tctl_limit, unit="C")),
        ]
        panel = self._metric_table("Power", rows)
        capability = self.collector.power.capability
        if capability.available and not self.collector.power.last_error:
            return panel
        details = self.collector.power.last_error or capability.reason
        return Panel(Group(panel.renderable, Text(details, style="yellow")), title="Power", border_style="yellow")

    def _render_battery_panel(self, state: AppState) -> Panel:
        battery = state.snapshot.battery
        capability = state.snapshot.capabilities.get("battery", Capability(False, "Battery unavailable"))
        rows = [
            ("Charge", _fmt_percent(battery.percent)),
            ("Status", battery.status or "Unavailable"),
            ("Power", _fmt_power(battery.power_w)),
            ("Alerts", state.errors[0] if state.errors else "None"),
        ]
        panel = self._metric_table("Battery and Status", rows)
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")), title="Battery and Status", border_style="yellow")

    def _render_footer(self, state: AppState) -> Panel:
        help_text = Text.from_markup(
            "[bold]1[/] CPU  [bold]2[/] Power  [bold]3[/] Fan Profile  [bold]4[/] Fan Curve  [bold]5[/] Quick Presets  [bold]h[/] Help  [bold]q[/] Quit"
        )
        status = Text(state.message, style=state.message_style)
        return Panel(Group(help_text, status), border_style="magenta")

    def _render_menu(self, state: AppState) -> Panel:
        renderers = {
            "cpu": self._cpu_menu_panel,
            "power": self._power_menu_panel,
            "fan_profile": self._fan_profile_menu_panel,
            "fan_curve": self._fan_curve_menu_panel,
            "quick": self._quick_menu_panel,
            "help": self._help_menu_panel,
        }
        return renderers[state.active_menu]()

    def _cpu_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, (label, freq) in self.CPU_PRESETS.items():
            table.add_row(f"[bold]{key}[/]", f"{label} ({freq / 1_000_000:.2f} GHz)")
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="CPU Limit Presets", border_style="cyan")

    def _power_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, (label, preset_name) in self.POWER_PRESETS.items():
            preset = self.collector.power.POWER_PRESETS[preset_name]
            table.add_row(f"[bold]{key}[/]", f"{label} ({preset['stapm'] // 1000}W STAPM)")
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Power Presets", border_style="cyan")

    def _fan_profile_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, label in self.FAN_PROFILES.items():
            table.add_row(f"[bold]{key}[/]", label)
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Fan Profiles", border_style="cyan")

    def _fan_curve_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, name in self.FAN_CURVES.items():
            table.add_row(f"[bold]{key}[/]", name.replace("_", " ").title())
        table.add_row("[bold]d[/]", "Reset to firmware defaults")
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Fan Curve Presets", border_style="cyan")

    def _quick_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, preset in self.QUICK_PRESETS.items():
            table.add_row(f"[bold]{key}[/]", preset[0])
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Quick Presets", border_style="cyan")

    def _help_menu_panel(self) -> Panel:
        text = Text.from_markup(
            "This dashboard updates automatically.\n\n"
            "Use the numbered shortcuts to open a control menu.\n"
            "Unsupported backends stay visible but are marked unavailable.\n"
            "Press [bold]b[/], [bold]Esc[/], or [bold]q[/] to close a menu."
        )
        return Panel(text, title="Help", border_style="cyan")

    def _render_compact(self, state: AppState) -> Panel:
        lines = [
            f"CPU: {_fmt_temp(state.snapshot.cpu.temp_c)} | {_fmt_freq(state.snapshot.cpu.current_freq_mhz)}",
            f"AMD iGPU: {_fmt_temp(state.snapshot.amd_gpu.temp_c)} | {_fmt_power(state.snapshot.amd_gpu.power_w)}",
            f"NVIDIA: {_fmt_temp(state.snapshot.nvidia_gpu.temp_c)} | {_fmt_percent(state.snapshot.nvidia_gpu.util_percent)}",
            f"Fans: {_fmt_rpm(state.snapshot.cooling.cpu_fan_rpm)} / {_fmt_rpm(state.snapshot.cooling.gpu_fan_rpm)}",
            f"Battery: {_fmt_percent(state.snapshot.battery.percent)} {state.snapshot.battery.status or ''}",
            state.message,
            "Widen the terminal for the full dashboard.",
        ]
        return Panel("\n".join(lines), title="ROG Control", border_style="cyan")

    @staticmethod
    def _limit_value(value: Optional[float], limit: Optional[float], unit: str = "W") -> str:
        if value is None and limit is None:
            return "Unavailable"
        if unit == "C":
            left = f"{value:.1f} C" if value is not None else "Unavailable"
            right = f"{limit:.0f} C" if limit is not None else "Unavailable"
        else:
            left = f"{value:.1f} {unit}" if value is not None else "Unavailable"
            right = f"{limit:.1f} {unit}" if limit is not None else "Unavailable"
        return f"{left} / {right}"

    @staticmethod
    def _backend_badge(capability: Capability, last_error: str, label: str) -> Text:
        if last_error:
            return Text(f"{label}: Warning", style="bold yellow")
        return _capability_badge(capability, label)
