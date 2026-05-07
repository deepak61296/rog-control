"""Enhanced Rich-based terminal application for ROG Control with sci-fi green theme."""

from __future__ import annotations

import select
import signal
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

from src.config import Config
from src.core.cpu import CPUController
from src.core.fans import FanController
from src.core.power import PowerController, PowerInfo
from src.core.sensors import Capability, SystemSnapshot, SensorReader
from src.ui.theme import (
    NEON_GREEN, BRIGHT_GREEN, TEAL, CYAN, WARNING_YELLOW, ERROR_RED, ORANGE,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_GREEN, SCI_FI_DOUBLE, SCI_FI_BOX,
    ROG_THEME, temp_style, usage_style
)
from src.ui.widgets import (
    temperature_gauge, power_gauge, rpm_gauge, enhanced_sparkline,
    metric_panel, status_badge, header_panel, footer_panel, progress_bar_horizontal
)


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
    per_core_freqs: list[int] = field(default_factory=list)


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
                self.state.per_core_freqs = self.cpu.get_all_core_freqs()
                if snapshot.cpu.temp_c is not None:
                    self.state.cpu_temp_history = (self.state.cpu_temp_history + [snapshot.cpu.temp_c])[-60:]
                if snapshot.amd_gpu.temp_c is not None:
                    self.state.amd_gpu_temp_history = (self.state.amd_gpu_temp_history + [snapshot.amd_gpu.temp_c])[-60:]
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
                per_core_freqs=list(self.state.per_core_freqs),
            )


class RogControlApp:
    """Main Rich terminal application with sci-fi theme."""

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

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.console = Console(force_terminal=True, theme=ROG_THEME)
        self.state = AppState()
        self.collector = DataCollector(self.state)
        self._resize_flag = False
        signal.signal(signal.SIGWINCH, self._handle_resize)

    def _handle_resize(self, signum, frame) -> None:
        self._resize_flag = True

    def run(self) -> int:
        self.collector.start()
        with TerminalInput() as keyboard, Live(self.render(), console=self.console, screen=True, auto_refresh=False) as live:
            while self.state.running:
                key = keyboard.read_key(timeout=0.15)
                if key:
                    self.handle_key(key)
                if self._resize_flag:
                    self._resize_flag = False
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
        elif normalized == "6":
            self.state.active_menu = "governor"
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
        elif active == "governor":
            self._handle_governor_menu(key)
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

    def _handle_governor_menu(self, key: str) -> None:
        governors = self.collector.cpu.get_available_governors()
        try:
            idx = int(key) - 1
            if 0 <= idx < len(governors):
                governor = governors[idx]
                success, message = self.collector.cpu.set_governor(governor)
                self.collector.update_message(message, "green" if success else "red")
        except (ValueError, IndexError):
            pass
        self.state.active_menu = None

    def _get_gauge_width(self, terminal_width: int) -> int:
        if terminal_width >= 120:
            return 20
        elif terminal_width >= 100:
            return 16
        else:
            return 14

    def render(self) -> RenderableType:
        width = self.console.size.width
        height = self.console.size.height
        state = self.collector.current_state()
        if width < 90 or height < 25:
            return self._render_compact(state, width, height)

        gauge_width = self._get_gauge_width(width)
        small_gauge = max(12, gauge_width - 4)

        header = self._render_header(state)
        rows = [
            Columns([self._render_cpu_panel(state, gauge_width), self._render_cooling_panel(state, small_gauge)], equal=True, expand=True),
            Columns([self._render_amd_gpu_panel(state, small_gauge), self._render_nvidia_panel(state, small_gauge)], equal=True, expand=True),
            Columns([self._render_power_panel(state, small_gauge), self._render_battery_panel(state, small_gauge)], equal=True, expand=True),
            self._render_footer(state),
        ]
        if state.active_menu:
            rows.append(self._render_menu(state))
        return Group(header, *rows)

    def _render_header(self, state: AppState) -> Panel:
        snapshot = state.snapshot
        badges = [
            status_badge("CPU", snapshot.capabilities.get("cpu_hwmon", Capability(False)).available, NEON_GREEN, WARNING_YELLOW),
            status_badge("AMD GPU", snapshot.capabilities.get("amd_hwmon", Capability(False)).available, NEON_GREEN, WARNING_YELLOW),
            status_badge("NVIDIA", snapshot.capabilities.get("nvidia", Capability(False)).available, NEON_GREEN, WARNING_YELLOW),
            status_badge("RyzenAdj", self.collector.power.capability.available, NEON_GREEN, WARNING_YELLOW),
            status_badge("asusctl", self.collector.fans.capability.available, NEON_GREEN, WARNING_YELLOW),
        ]
        return header_panel("ROG CONTROL", "System Monitoring Dashboard", badges)

    def _render_cpu_panel(self, state: AppState, gauge_width: int = 16) -> Panel:
        cpu = state.snapshot.cpu
        temp_gauge = temperature_gauge(cpu.temp_c, width=gauge_width + 4)
        sparkline = enhanced_sparkline(state.cpu_temp_history, width=gauge_width + 4)

        # Per-core frequency display - adjust based on panel width
        max_cores = 8 if gauge_width >= 18 else (6 if gauge_width >= 16 else 4)
        core_freqs = state.per_core_freqs[:max_cores]
        cores_per_row = 2 if max_cores > 4 else 2
        core_text = Text()
        for i, freq in enumerate(core_freqs):
            ghz = freq / 1000.0 if freq else 0
            style = temp_style(cpu.temp_c) if cpu.temp_c else TEXT_SECONDARY
            core_text.append(f"C{i}:{ghz:.1f}G ", style=style)
            if (i + 1) % cores_per_row == 0:
                core_text.append("\n")

        metrics = [
            ("Temperature", temp_gauge),
            ("Current", f"{cpu.current_freq_mhz or 0:.0f} MHz" if cpu.current_freq_mhz else "---"),
            ("Limit", f"{cpu.max_freq_mhz or 0:.0f} MHz" if cpu.max_freq_mhz else "---"),
            ("Governor", Text(cpu.governor or "Unavailable", style="bold")),
            ("Trend", sparkline),
            ("Cores", core_text or "Unavailable"),
        ]
        return metric_panel("CPU", metrics, NEON_GREEN)

    def _render_cooling_panel(self, state: AppState, gauge_width: int = 12) -> Panel:
        cooling = state.snapshot.cooling
        fan_status = "Enabled" if state.custom_curve_enabled else "Disabled"
        if state.custom_curve_enabled is None:
            fan_status = "Unavailable"

        metrics = [
            ("CPU Fan", rpm_gauge(cooling.cpu_fan_rpm, width=gauge_width)),
            ("GPU Fan", rpm_gauge(cooling.gpu_fan_rpm, width=gauge_width)),
            ("Profile", Text(state.fan_profile or "Unavailable", style="bold")),
            ("Custom Curve", Text(fan_status, style="bold green" if state.custom_curve_enabled else "bold yellow")),
            ("NVMe Temp", temperature_gauge(state.snapshot.nvme_temp_c, width=gauge_width)),
        ]

        capability = self.collector.fans.capability
        details = self.collector.fans.last_error or capability.reason
        panel = metric_panel("Cooling", metrics, BORDER_GREEN)
        if capability.available and not details:
            return panel
        return Panel(Group(panel.renderable, Text(details or "Cooling controls healthy", style="yellow")),
                     title="Cooling", border_style="yellow", box=SCI_FI_BOX)

    def _render_amd_gpu_panel(self, state: AppState, gauge_width: int = 12) -> Panel:
        gpu = state.snapshot.amd_gpu
        capability = state.snapshot.capabilities.get("amd_hwmon", Capability(False))

        metrics = [
            ("Temperature", temperature_gauge(gpu.temp_c, width=gauge_width)),
            ("Clock", f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else "Unavailable"),
            ("Power", power_gauge(gpu.power_w, width=gauge_width)),
            ("Trend", enhanced_sparkline(state.amd_gpu_temp_history, width=gauge_width)),
        ]

        panel = metric_panel("AMD iGPU", metrics, TEAL)
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")),
                     title="AMD iGPU", border_style="yellow", box=SCI_FI_BOX)

    def _render_nvidia_panel(self, state: AppState, gauge_width: int = 12) -> Panel:
        gpu = state.snapshot.nvidia_gpu
        capability = state.snapshot.capabilities.get("nvidia", Capability(False))

        metrics = [
            ("Temperature", temperature_gauge(gpu.temp_c, width=gauge_width)),
            ("Clock", f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else "Unavailable"),
            ("Power", power_gauge(gpu.power_w, width=gauge_width)),
            ("Utilization", progress_bar_horizontal(gpu.util_percent or 0, 100, width=gauge_width, show_percent=True) if gpu.util_percent else "---"),
            ("VRAM", f"{gpu.vram_used_mb}/{gpu.vram_total_mb} MB" if gpu.vram_used_mb is not None and gpu.vram_total_mb is not None else "Unavailable"),
        ]

        panel = metric_panel("NVIDIA dGPU", metrics, CYAN)
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")),
                     title="NVIDIA dGPU", border_style="yellow", box=SCI_FI_BOX)

    def _render_power_panel(self, state: AppState, gauge_width: int = 12) -> Panel:
        info = state.power_info

        metrics = [
            ("STAPM", power_gauge(info.stapm_value, info.stapm_limit, width=gauge_width)),
            ("Fast PPT", power_gauge(info.fast_value, info.fast_limit, width=gauge_width)),
            ("Slow PPT", power_gauge(info.slow_value, info.slow_limit, width=gauge_width)),
            ("Thermal Limit", temperature_gauge(info.tctl_value, width=gauge_width)),
        ]

        panel = metric_panel("Power", metrics, ORANGE)
        capability = self.collector.power.capability
        if capability.available and not self.collector.power.last_error:
            return panel
        details = self.collector.power.last_error or capability.reason
        return Panel(Group(panel.renderable, Text(details, style="yellow")),
                     title="Power", border_style="yellow", box=SCI_FI_BOX)

    def _render_battery_panel(self, state: AppState, gauge_width: int = 12) -> Panel:
        battery = state.snapshot.battery
        capability = state.snapshot.capabilities.get("battery", Capability(False))

        metrics = [
            ("Charge", progress_bar_horizontal(battery.percent or 0, 100, width=gauge_width) if battery.percent else "---"),
            ("Status", Text(battery.status or "Unavailable", style="bold")),
            ("Power", power_gauge(battery.power_w, width=gauge_width)),
            ("Alerts", Text(state.errors[0] if state.errors else "None", style="bold yellow" if state.errors else "bold green")),
        ]

        panel = metric_panel("Battery & Status", metrics, BRIGHT_GREEN)
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")),
                     title="Battery & Status", border_style="yellow", box=SCI_FI_BOX)

    def _render_footer(self, state: AppState) -> Panel:
        help_text = Text.from_markup(
            "[bold primary]1[/] CPU  [bold primary]2[/] Power  [bold primary]3[/] Fan  [bold primary]4[/] Curve  "
            "[bold primary]5[/] Quick  [bold primary]6[/] Gov  [bold primary]h[/] Help  [bold primary]q[/] Quit"
        )
        status = Text(state.message, style=state.message_style)
        return footer_panel(help_text.markup, status.plain, state.message_style)

    def _render_menu(self, state: AppState) -> Panel:
        renderers = {
            "cpu": self._cpu_menu_panel,
            "power": self._power_menu_panel,
            "fan_profile": self._fan_profile_menu_panel,
            "fan_curve": self._fan_curve_menu_panel,
            "quick": self._quick_menu_panel,
            "governor": self._governor_menu_panel,
            "help": self._help_menu_panel,
        }
        return renderers[state.active_menu]()

    def _cpu_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, (label, freq) in self.CPU_PRESETS.items():
            table.add_row(f"[bold primary]{key}[/]", f"{label} ({freq / 1000000:.2f} GHz)")
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="CPU Frequency Limit", border_style=CYAN, box=SCI_FI_BOX)

    def _power_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, (label, preset_name) in self.POWER_PRESETS.items():
            preset = self.collector.power.POWER_PRESETS[preset_name]
            table.add_row(f"[bold primary]{key}[/]", f"{label} ({preset['stapm'] // 1000}W STAPM)")
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Power Presets", border_style=CYAN, box=SCI_FI_BOX)

    def _fan_profile_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, label in self.FAN_PROFILES.items():
            table.add_row(f"[bold primary]{key}[/]", label)
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Fan Profiles", border_style=CYAN, box=SCI_FI_BOX)

    def _fan_curve_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, name in self.FAN_CURVES.items():
            table.add_row(f"[bold primary]{key}[/]", name.replace("_", " ").title())
        table.add_row("[bold primary]d[/]", "Reset to firmware defaults")
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Fan Curve Presets", border_style=CYAN, box=SCI_FI_BOX)

    def _quick_menu_panel(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for key, preset in self.QUICK_PRESETS.items():
            table.add_row(f"[bold primary]{key}[/]", preset[0])
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="Quick Presets", border_style=CYAN, box=SCI_FI_BOX)

    def _governor_menu_panel(self) -> Panel:
        governors = self.collector.cpu.get_available_governors()
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        for idx, gov in enumerate(governors, 1):
            table.add_row(f"[bold primary]{idx}[/]", gov)
        table.add_row("[bold]b[/]", "Back")
        return Panel(table, title="CPU Governor", border_style=CYAN, box=SCI_FI_BOX)

    def _help_menu_panel(self) -> Panel:
        text = Text.from_markup(
            "[bold primary]ROG Control[/] - System Monitoring & Control\n\n"
            "• [bold]1-6[/] Open control menus\n"
            "• [bold]b/ESC/q[/] Close menu\n"
            "• [bold]h[/] Toggle this help\n"
            "• [bold]r[/] Refresh (auto-updates)\n\n"
            "Backends marked [bold green]●[/] are active\n"
            "Temperature colors: [green]Normal[/] [yellow]Warning[/] [red]Critical[/]"
        )
        return Panel(text, title="Help", border_style=CYAN, box=SCI_FI_BOX)

    def _render_compact(self, state: AppState, width: int = 90, height: int = 25) -> Panel:
        reasons = []
        if width < 90:
            reasons.append(f"width ({width}<90)")
        if height < 25:
            reasons.append(f"height ({height}<25)")
        reason_msg = ", ".join(reasons) if reasons else "unknown"

        lines = [
            f"CPU: {state.snapshot.cpu.temp_c or '---'}°C | {state.snapshot.cpu.current_freq_mhz or '---'} MHz",
            f"AMD iGPU: {state.snapshot.amd_gpu.temp_c or '---'}°C | {state.snapshot.amd_gpu.power_w or '---'}W",
            f"NVIDIA: {state.snapshot.nvidia_gpu.temp_c or '---'}°C | {state.snapshot.nvidia_gpu.util_percent or '---'}%",
            f"Fans: {state.snapshot.cooling.cpu_fan_rpm or '---'} / {state.snapshot.cooling.gpu_fan_rpm or '---'} RPM",
            f"Battery: {state.snapshot.battery.percent or '---'}% {state.snapshot.battery.status or ''}",
            state.message,
            f"[dim]Terminal too small: {reason_msg}[/]",
        ]
        return Panel("\n".join(lines), title="ROG Control", border_style=CYAN, box=SCI_FI_BOX)