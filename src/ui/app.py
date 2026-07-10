"""Modern Textual TUI for ROG Control."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Grid, Container
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Static, TabbedContent, TabPane

from src.ui.actions import ControlAction, execute_control_action
from src.ui.collector import DataCollector
from src.ui.state import AppState
from src.ui.widgets import BrailleGraph, GaugeBar, build_core_strip

logger = logging.getLogger(__name__)

PANEL_TITLES = {
    "cpu": "CPU",
    "power": "Power",
    "fans": "Fans",
    "quick": "Quick",
}
PANEL_ORDER = ("cpu", "power", "fans", "quick")

COLOR_UTIL = "#39ff14"
COLOR_TEMP = "#ff0033"
COLOR_VRAM = "#00e5ff"
COLOR_DIM = "#6e7681"


def read_cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    for marker in (" w/ ", " with "):
                        if marker in model:
                            model = model.split(marker, 1)[0]
                    return model.strip()
    except OSError:
        pass
    return "CPU"


class StatStrip(Static):
    """Single line of `LABEL value` pairs with per-value colors."""

    def set_stats(self, items: list[tuple[str, str, str]]) -> None:
        text = Text(no_wrap=True, overflow="ellipsis")
        for index, (label, value, color) in enumerate(items):
            if index:
                text.append("  ")
            if label:
                text.append(f"{label} ", style=COLOR_DIM)
            text.append(value, style=f"bold {color}")
        self.update(text)


class ConfirmScreen(ModalScreen[bool]):
    """Small confirmation modal for risky hardware actions."""

    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: 54;
        height: auto;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
    }

    #confirm-message {
        margin-bottom: 1;
    }

    #confirm-buttons {
        height: auto;
        align-horizontal: right;
    }

    #confirm-buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("n", "cancel", "No", show=False),
        Binding("y", "confirm", "Yes", show=False),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", id="confirm-cancel")
                yield Button("Apply", id="confirm-apply", variant="warning")

    @on(Button.Pressed, "#confirm-cancel")
    def _cancel_pressed(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm-apply")
    def _apply_pressed(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)


class CPUPanel(Static):
    """CPU utilization/temperature graph with stats and per-core strip."""

    def compose(self) -> ComposeResult:
        self.stats = StatStrip(classes="stat-strip")
        yield self.stats
        self.legend = StatStrip(classes="legend")
        yield self.legend
        self.graph = BrailleGraph(max_value=100.0)
        yield self.graph
        self.cores = Static(classes="core-strip")
        yield self.cores

    def on_mount(self) -> None:
        self.border_title = f"⡷ CPU · {read_cpu_model()}"

    def update_state(self, state: AppState) -> None:
        cpu = state.snapshot.cpu
        temp = f"{cpu.temp_c:.0f}°C" if cpu.temp_c is not None else "---"
        freq = f"{cpu.current_freq_mhz / 1000:.2f}GHz" if cpu.current_freq_mhz is not None else "---"
        cap = f"{cpu.max_freq_mhz / 1000:.2f}GHz" if cpu.max_freq_mhz is not None else "---"
        power = f"{state.power_info.stapm_value:.1f}W" if state.power_info.stapm_value is not None else "---"
        load = f"{cpu.util_percent:.0f}%" if cpu.util_percent is not None else "---"
        self.stats.set_stats(
            [
                ("TEMP", temp, COLOR_TEMP),
                ("FREQ", freq, COLOR_UTIL),
                ("CAP", cap, "#e6edf3"),
                ("PWR", power, "#ffb700"),
                ("GOV", cpu.governor or "---", "#e6edf3"),
                ("LOAD", load, COLOR_UTIL),
            ]
        )
        self.legend.set_stats(
            [
                ("", f"⣿ UTIL {load}", COLOR_UTIL),
                ("", f"⣿ TEMP {temp}", COLOR_TEMP),
            ]
        )
        self.graph.set_series(
            [
                (state.cpu_util_history, COLOR_UTIL),
                (state.cpu_temp_history, COLOR_TEMP),
            ]
        )
        self.cores.update(build_core_strip(cpu.per_core_util, cpu.per_core_freq_mhz))


class GPUPanel(Static):
    """NVIDIA dGPU utilization/VRAM graph with stats."""

    def compose(self) -> ComposeResult:
        self.stats = StatStrip(classes="stat-strip")
        yield self.stats
        self.legend = StatStrip(classes="legend")
        yield self.legend
        self.graph = BrailleGraph(max_value=100.0)
        yield self.graph

    def on_mount(self) -> None:
        self.border_title = "⣾ GPU · NVIDIA"

    def set_gpu_name(self, name: str | None) -> None:
        if name:
            self.border_title = f"⣾ GPU · {name}"

    def update_state(self, state: AppState) -> None:
        gpu = state.snapshot.nvidia_gpu
        temp = f"{gpu.temp_c:.0f}°C" if gpu.temp_c is not None else "---"
        clock = f"{gpu.clock_mhz}MHz" if gpu.clock_mhz is not None else "---"
        power = f"{gpu.power_w:.1f}W" if gpu.power_w is not None else "---"
        util = f"{gpu.util_percent}%" if gpu.util_percent is not None else "---"
        if gpu.vram_used_mb is not None and gpu.vram_total_mb:
            vram = f"{gpu.vram_used_mb / 1024:.1f}/{gpu.vram_total_mb / 1024:.1f}GB"
            vram_pct = f"{gpu.vram_used_mb / gpu.vram_total_mb * 100:.0f}%"
        else:
            vram, vram_pct = "---", "---"
        self.stats.set_stats(
            [
                ("TEMP", temp, COLOR_TEMP),
                ("CLK", clock, COLOR_UTIL),
                ("PWR", power, "#ffb700"),
                ("VRAM", vram, COLOR_VRAM),
            ]
        )
        self.legend.set_stats(
            [
                ("", f"⣿ UTIL {util}", COLOR_UTIL),
                ("", f"⣿ VRAM {vram_pct}", COLOR_VRAM),
            ]
        )
        self.graph.set_series(
            [
                (state.gpu_util_history, COLOR_UTIL),
                (state.vram_util_history, COLOR_VRAM),
            ]
        )


class MemoryPanel(Static):
    """RAM and swap gauges."""

    def compose(self) -> ComposeResult:
        self.ram = GaugeBar("RAM", label_width=5)
        yield self.ram
        self.swap = GaugeBar("SWAP", label_width=5)
        yield self.swap
        self.detail = StatStrip(classes="stat-strip")
        yield self.detail

    def on_mount(self) -> None:
        self.border_title = "⡪ MEMORY"

    def update_state(self, state: AppState) -> None:
        memory = state.snapshot.memory

        def gb(value_mb: int | None) -> str:
            return f"{value_mb / 1024:.1f}" if value_mb is not None else "?"

        if memory.total_mb:
            self.ram.set_gauge(memory.used_mb, memory.total_mb, f"{gb(memory.used_mb)}/{gb(memory.total_mb)}G")
        else:
            self.ram.set_gauge(None, None, "---")
        if memory.swap_total_mb:
            self.swap.set_gauge(memory.swap_used_mb, memory.swap_total_mb, f"{gb(memory.swap_used_mb)}/{gb(memory.swap_total_mb)}G")
        else:
            self.swap.set_gauge(None, None, "---")
        available = f"{gb(memory.available_mb)}G" if memory.available_mb is not None else "---"
        self.detail.set_stats([("AVAIL", available, "#e6edf3")])


class PowerPanel(Static):
    """RyzenAdj limit gauges: measured value against configured limit."""

    def compose(self) -> ComposeResult:
        self.stapm = GaugeBar("STAPM", label_width=6)
        yield self.stapm
        self.fast = GaugeBar("FAST", label_width=6)
        yield self.fast
        self.slow = GaugeBar("SLOW", label_width=6)
        yield self.slow
        self.tctl = GaugeBar("TCTL", label_width=6)
        yield self.tctl

    def on_mount(self) -> None:
        self.border_title = "⢾ POWER LIMITS"

    def update_state(self, state: AppState) -> None:
        info = state.power_info

        def apply(gauge: GaugeBar, value: float | None, limit: float | None, unit: str) -> None:
            if value is None and limit is None:
                gauge.set_gauge(None, None, "---")
                return
            value_text = f"{value:.1f}" if value is not None else "?"
            limit_text = f"{limit:.0f}" if limit is not None else "?"
            gauge.set_gauge(value, limit, f"{value_text}/{limit_text}{unit}")

        apply(self.stapm, info.stapm_value, info.stapm_limit, "W")
        apply(self.fast, info.fast_value, info.fast_limit, "W")
        apply(self.slow, info.slow_value, info.slow_limit, "W")
        apply(self.tctl, info.tctl_value, info.tctl_limit, "°")


class SystemPanel(Static):
    """Fans, iGPU, battery, NVMe, and active profile."""

    def compose(self) -> ComposeResult:
        self.fans = StatStrip(classes="stat-strip")
        yield self.fans
        self.igpu = StatStrip(classes="stat-strip")
        yield self.igpu
        self.battery = GaugeBar("BAT", label_width=4, high_is_good=True)
        yield self.battery
        self.other = StatStrip(classes="stat-strip")
        yield self.other

    def on_mount(self) -> None:
        self.border_title = "⣠ SYSTEM"

    def update_state(self, state: AppState) -> None:
        cooling = state.snapshot.cooling
        cpu_fan = f"{cooling.cpu_fan_rpm}" if cooling.cpu_fan_rpm else "---"
        gpu_fan = f"{cooling.gpu_fan_rpm}" if cooling.gpu_fan_rpm else "---"
        curve = "---"
        if state.custom_curve_enabled is not None:
            curve = "CUSTOM" if state.custom_curve_enabled else "FIRMWARE"
        self.fans.set_stats(
            [
                ("FANS", f"{cpu_fan}/{gpu_fan}rpm", COLOR_UTIL),
                ("CURVE", curve, "#e6edf3"),
            ]
        )

        igpu = state.snapshot.amd_gpu
        busy = f"{igpu.busy_percent}%" if igpu.busy_percent is not None else "---"
        igpu_temp = f"{igpu.temp_c:.0f}°C" if igpu.temp_c is not None else "---"
        igpu_clock = f"{igpu.clock_mhz}MHz" if igpu.clock_mhz is not None else "---"
        igpu_power = f"{igpu.power_w:.1f}W" if igpu.power_w is not None else "---"
        self.igpu.set_stats(
            [
                ("iGPU", busy, COLOR_UTIL),
                ("", igpu_temp, COLOR_TEMP),
                ("", igpu_clock, "#e6edf3"),
                ("", igpu_power, "#ffb700"),
            ]
        )

        battery = state.snapshot.battery
        if battery.percent is not None:
            status = (battery.status or "").upper()[:11]
            power = f" {battery.power_w:.1f}W" if battery.power_w else ""
            self.battery.set_gauge(battery.percent, 100.0, f"{battery.percent}% {status}{power}".strip())
        else:
            self.battery.set_gauge(None, None, "---")

        nvme = f"{state.snapshot.nvme_temp_c:.0f}°C" if state.snapshot.nvme_temp_c is not None else "---"
        self.other.set_stats(
            [
                ("NVME", nvme, COLOR_TEMP),
                ("PROFILE", state.fan_profile or "---", COLOR_UTIL),
            ]
        )


class RogControlApp(App[None]):
    """Main Textual application."""

    TITLE = "ROG CONTROL"
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    $primary: #39ff14;
    $secondary: #ff0033;
    $success: #39ff14;
    $warning: #ff0033;
    $surface: #0a0d10;
    $background: #030304;
    $text-muted: #6e7681;

    Screen {
        layout: vertical;
        background: $background;
    }

    Header {
        background: $background;
        color: $primary;
        text-style: bold;
    }

    #main-grid {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 1fr 36;
        height: 1fr;
    }

    #dashboard {
        layout: vertical;
        padding: 0 1;
        overflow-y: auto;
    }

    .panel {
        border: round #1d5c26;
        border-title-color: $primary;
        border-title-style: bold;
        background: $surface;
        padding: 0 1;
    }

    CPUPanel {
        height: 2fr;
        min-height: 10;
        margin-bottom: 0;
    }

    GPUPanel {
        height: 2fr;
        min-height: 9;
    }

    #bottom-row {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 3fr 4fr 5fr;
        grid-gutter: 0 1;
        height: 8;
        min-height: 8;
    }

    MemoryPanel, PowerPanel, SystemPanel {
        height: 100%;
    }

    .stat-strip, .legend, .core-strip {
        height: 1;
    }

    .legend {
        color: $text-muted;
    }

    GaugeBar {
        margin-bottom: 0;
    }

    .control-pane {
        border-left: vkey #1d5c26;
        background: $surface;
        padding: 0 1;
        overflow-y: auto;
    }

    TabbedContent {
        height: auto;
    }

    TabPane {
        padding: 1 0;
    }

    .action-button {
        width: 100%;
        margin-bottom: 1;
    }

    .action-button.-primary {
        background: $primary 15%;
        color: $primary;
        border: tall $primary;
    }
    .action-button.-primary:hover {
        background: $primary;
        color: black;
    }

    .action-button.-warning {
        background: $secondary 15%;
        color: $secondary;
        border: tall $secondary;
    }
    .action-button.-warning:hover {
        background: $secondary;
        color: white;
    }

    .action-detail {
        color: $text-muted;
        margin-left: 1;
        margin-bottom: 1;
        height: auto;
    }

    #status-bar {
        height: 1;
        padding: 0 1;
        background: $primary;
        color: black;
        text-style: bold;
        overflow: hidden;
    }
    """

    BINDINGS = [
        Binding("1", "shortcut_1", "CPU"),
        Binding("2", "shortcut_2", "Power"),
        Binding("3", "shortcut_3", "Fans"),
        Binding("4", "shortcut_4", "Quick"),
        Binding("b", "back", "Back", show=False),
        Binding("escape", "back", "Back", show=False),
        Binding("ctrl+c", "quit_app", "Quit"),
    ]

    CPU_PRESETS = {
        "1": ("Silent cap", 2500000),
        "2": ("Cool cap", 3000000),
        "3": ("Balanced cap", 3500000),
        "4": ("Performance cap", 4000000),
        "5": ("High cap", 4500000),
    }
    POWER_PRESETS = {
        "1": ("Silent", "silent"),
        "2": ("Eco", "eco"),
        "3": ("Cool", "cool"),
        "4": ("Balanced", "balanced"),
        "5": ("Performance", "performance"),
        "6": ("High", "high"),
    }
    FAN_CURVES = {"1": "aggressive", "2": "max"}
    QUICK_PRESETS = {
        "1": {
            "name": "Ultra Battery Saver",
            "freq": 1500000,
            "power": "silent",
            "fan_profile": "Quiet",
            "fan_mode": "firmware",
            "description": "1.50 GHz, 15W, Quiet, firmware fans.",
        },
        "2": {
            "name": "Battery Saver",
            "freq": 2500000,
            "power": "silent",
            "fan_profile": "Quiet",
            "fan_mode": "firmware",
            "description": "2.50 GHz, 15W, Quiet, firmware fans.",
        },
        "3": {
            "name": "Battery Performance",
            "freq": 3000000,
            "power": "battery",
            "fan_profile": "Balanced",
            "fan_mode": "firmware",
            "description": "3.00 GHz, 25W, Balanced, firmware fans.",
        },
        "4": {
            "name": "PD Productivity",
            "freq": 2500000,
            "power": "pd",
            "fan_profile": "Balanced",
            "fan_mode": "firmware",
            "description": "2.50 GHz, 20W, Balanced, firmware fans.",
        },
        "5": {
            "name": "OEM Performance",
            "freq": 3000000,
            "power": "ac",
            "fan_profile": "Performance",
            "fan_mode": "max",
            "description": "3.00 GHz, 30W, Performance, max fans.",
            "confirmation": "Apply OEM Performance (30W with max fans)? Use only with the 240W ASUS adapter.",
        },
    }

    def __init__(self, collector: DataCollector | None = None) -> None:
        super().__init__()
        self.state = getattr(collector, "state", AppState())
        self.collector = collector or DataCollector(self.state)
        self.running_action: ControlAction | None = None
        self.actions = self._build_actions()

        self.actions_by_panel: dict[str, list[ControlAction]] = defaultdict(list)
        self.actions_by_key: dict[str, dict[str, ControlAction]] = defaultdict(dict)
        self.actions_by_button_id: dict[str, ControlAction] = {}
        for action in self.actions:
            self.actions_by_panel[action.panel].append(action)
            self.actions_by_key[action.panel][action.key] = action

        self.active_control_panel: str | None = "cpu"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-grid"):
            with Vertical(id="dashboard"):
                self.cpu_panel = CPUPanel(classes="panel")
                yield self.cpu_panel
                self.gpu_panel = GPUPanel(classes="panel")
                yield self.gpu_panel
                with Horizontal(id="bottom-row"):
                    self.memory_panel = MemoryPanel(classes="panel")
                    yield self.memory_panel
                    self.power_panel = PowerPanel(classes="panel")
                    yield self.power_panel
                    self.system_panel = SystemPanel(classes="panel")
                    yield self.system_panel

            with Vertical(classes="control-pane"):
                with TabbedContent(id="tabs"):
                    for panel in PANEL_ORDER:
                        with TabPane(PANEL_TITLES[panel], id=f"tab-{panel}"):
                            for action in self.actions_by_panel[panel]:
                                btn_id = f"action-{action.id}"
                                self.actions_by_button_id[btn_id] = action
                                yield Button(
                                    f"{action.key}  {action.label}",
                                    id=btn_id,
                                    classes="action-button",
                                    variant="warning" if action.confirmation else "primary",
                                )
                                yield Label(action.description, classes="action-detail")

        self.status_bar = Label("System Monitoring Active", id="status-bar")
        yield self.status_bar
        yield Footer()

    def on_mount(self) -> None:
        gpu_name = getattr(getattr(self.collector, "sensors", None), "gpu_name", None)
        self.gpu_panel.set_gpu_name(gpu_name)
        self.collector.start()
        self.set_interval(0.5, self.refresh_dashboard)
        self.refresh_dashboard()

    def on_unmount(self) -> None:
        self.collector.stop()

    def refresh_dashboard(self) -> None:
        state = self.collector.current_state()
        self.cpu_panel.update_state(state)
        self.gpu_panel.update_state(state)
        self.memory_panel.update_state(state)
        self.power_panel.update_state(state)
        self.system_panel.update_state(state)

        for action in self.actions:
            button = self.query_one(f"#action-{action.id}", Button)
            button.disabled = self.running_action is not None or not self._action_available(action, state)

        if self.running_action:
            self.status_bar.update(f"Running action: {self.running_action.label}...")
        elif self._recent_status_message(state):
            self.status_bar.update(self._recent_status_message(state))
        elif state.errors:
            error_line = state.errors[0].strip().split("\n")[0]
            self.status_bar.update(f"WARNING: {error_line}")
        else:
            self.status_bar.update("System Monitoring Active | All Systems Nominal")

    @on(Button.Pressed)
    def _button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        action = self.actions_by_button_id.get(button_id)
        if action is not None:
            self._request_action(action)

    def action_shortcut_1(self) -> None: self._handle_shortcut("1")
    def action_shortcut_2(self) -> None: self._handle_shortcut("2")
    def action_shortcut_3(self) -> None: self._handle_shortcut("3")
    def action_shortcut_4(self) -> None: self._handle_shortcut("4")
    def action_back(self) -> None:
        if self.active_control_panel is not None:
            self.active_control_panel = None
            self.notify("Controls unfocused. Press 1-4 to select a panel.", severity="information")
        else:
            self.exit()

    @on(TabbedContent.TabActivated)
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane.id and event.pane.id.startswith("tab-"):
            self.active_control_panel = event.pane.id.replace("tab-", "")

    def _handle_shortcut(self, key: str) -> None:
        panel_map = {"1": "cpu", "2": "power", "3": "fans", "4": "quick"}
        if key not in panel_map:
            return

        panel = panel_map[key]
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = f"tab-{panel}"
        self.active_control_panel = panel

    def action_quit_app(self) -> None:
        self.exit()

    def _request_action(self, action: ControlAction) -> None:
        if self.running_action is not None:
            self.notify(f"Still running: {self.running_action.label}", severity="warning")
            return
        if not self._action_available(action, self.collector.current_state()):
            self.notify(f"Unavailable: {action.label}", severity="error")
            return
        if action.confirmation:
            self.push_screen(ConfirmScreen(action.confirmation), lambda confirmed: self._confirmed_action(action, confirmed))
            return
        self._start_action(action)

    def _confirmed_action(self, action: ControlAction, confirmed: bool) -> None:
        if confirmed:
            self._start_action(action)
        else:
            self.notify("Action Cancelled.", severity="information")

    def _start_action(self, action: ControlAction) -> None:
        self.running_action = action
        threading.Thread(
            target=self._run_control_action,
            args=(action,),
            daemon=True,
        ).start()
        self.refresh_dashboard()

    def _run_control_action(self, action: ControlAction) -> None:
        try:
            success, message = execute_control_action(action, self.collector)
        except Exception as exc:
            logger.exception("Control action failed")
            success, message = False, f"{action.label} failed: {exc}"
        try:
            self.call_from_thread(self._finish_action, action, success, message)
        except RuntimeError:
            pass

    def _finish_action(self, action: ControlAction, success: bool, message: str) -> None:
        self.running_action = None
        self.collector.update_message(message, "cyan" if success else "red")
        if not success:
            self.notify(self._notification_text(message), severity="error")
        self.refresh_dashboard()

    @staticmethod
    def _notification_text(message: str, limit: int = 96) -> str:
        cleaned = " ".join(message.split())
        if len(cleaned) <= limit:
            return cleaned
        return f"{cleaned[: limit - 1].rstrip()}..."

    @staticmethod
    def _recent_status_message(state: AppState) -> str:
        if not state.message or state.message == "Press h for help.":
            return ""
        if time.time() - state.message_time > 8.0:
            return ""
        return state.message.strip().split("\n")[0]

    @staticmethod
    def _action_available(action: ControlAction, state: AppState) -> bool:
        availability = {
            "cpu": state.cpu_capability.available,
            "power": state.power_capability.available,
            "fan": state.fan_capability.available,
        }
        return all(availability.get(capability, False) for capability in action.capabilities)

    def _build_actions(self) -> list[ControlAction]:
        actions: list[ControlAction] = []
        for key, (label, freq) in self.CPU_PRESETS.items():
            actions.append(
                ControlAction(
                    id=f"cpu-{key}",
                    panel="cpu",
                    key=key,
                    label=label,
                    description=f"Max CPU frequency {freq / 1_000_000:.2f} GHz.",
                    kind="cpu_freq",
                    payload={"freq": freq},
                    capabilities=("cpu",),
                )
            )

        for key, (label, preset_name) in self.POWER_PRESETS.items():
            preset = self.collector.power.POWER_PRESETS.get(preset_name, {})
            watts = preset.get("stapm", 0) // 1000
            confirmation = None
            if watts >= 55:
                confirmation = f"Apply {label} power preset ({watts}W STAPM)?"
            actions.append(
                ControlAction(
                    id=f"power-{key}",
                    panel="power",
                    key=key,
                    label=label,
                    description=f"RyzenAdj {watts}W STAPM limit.",
                    kind="power_preset",
                    payload={"preset": preset_name},
                    capabilities=("power",),
                    confirmation=confirmation,
                )
            )

        for key, preset in self.FAN_CURVES.items():
            confirmation = "Set fans to 100%?" if preset == "max" else None
            actions.append(
                ControlAction(
                    id=f"fan-curve-{key}",
                    panel="fans",
                    key=key,
                    label=preset.replace("_", " ").title(),
                    description="Apply custom fan curve.",
                    kind="fan_curve",
                    payload={"preset": preset},
                    capabilities=("fan",),
                    confirmation=confirmation,
                )
            )
        actions.append(
            ControlAction(
                id="fan-curve-reset",
                panel="fans",
                key="3",
                label="Firmware Default",
                description="Reset to firmware fan control.",
                kind="fan_reset",
                payload={},
                capabilities=("fan",),
            )
        )

        for key, preset in self.QUICK_PRESETS.items():
            name = str(preset["name"])
            actions.append(
                ControlAction(
                    id=f"quick-{key}",
                    panel="quick",
                    key=key,
                    label=name,
                    description=str(preset["description"]),
                    kind="quick_preset",
                    payload=preset,
                    capabilities=("cpu", "power", "fan"),
                    confirmation=str(preset["confirmation"]) if "confirmation" in preset else None,
                )
            )
        return actions
