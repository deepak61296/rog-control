"""Textual terminal application for ROG Control."""

from __future__ import annotations

from collections import defaultdict
import logging
import threading

from rich.align import Align
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Static

from src.core.sensors import Capability
from src.ui.actions import ControlAction, execute_control_action
from src.ui.collector import DataCollector
from src.ui.formatters import fmt_freq, fmt_percent, fmt_power, fmt_rpm, fmt_temp, limit_str, sparkline
from src.ui.state import AppState

logger = logging.getLogger(__name__)


PANEL_TITLES = {
    "cpu": "CPU Limits",
    "power": "Power Presets",
    "fan_profile": "Fan Profiles",
    "fan_curve": "Fan Curves",
    "quick": "Quick Presets",
}
PANEL_DOM_IDS = {
    "cpu": "cpu",
    "power": "power",
    "fan_profile": "fan-profile",
    "fan_curve": "fan-curve",
    "quick": "quick",
}
PANEL_ORDER = ("cpu", "power", "fan_profile", "fan_curve", "quick")


def _capability_badge(capability: Capability, label: str, last_error: str = "") -> Text:
    if last_error:
        return Text(f"{label}: Warning", style="bold yellow")
    if capability.available:
        return Text("\u25cf " + label, style="green bold")
    return Text("\u25cb " + label, style="yellow bold")


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


class RogControlApp(App[None]):
    """Main Textual application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #content {
        height: 1fr;
    }

    #dashboard {
        width: 1fr;
        padding: 0 1;
    }

    .dashboard-row {
        height: 1fr;
        min-height: 9;
    }

    .metric-card {
        width: 1fr;
        height: 100%;
        min-height: 8;
        padding: 0 1;
    }

    #header-card {
        height: auto;
        min-height: 5;
        padding: 0 1;
    }

    #controls {
        width: 42;
        border-left: solid $accent;
        padding: 0 1;
    }

    #control-title {
        text-style: bold;
        margin: 1 0;
    }

    #control-tabs {
        height: auto;
        margin-bottom: 1;
    }

    #control-tabs Button {
        width: 1fr;
        min-width: 6;
    }

    .control-section {
        padding-bottom: 1;
    }

    .section-heading {
        text-style: bold;
        margin: 1 0 0 0;
    }

    .action-button {
        width: 100%;
        margin-top: 1;
    }

    .action-detail {
        color: $text-muted;
        margin-left: 1;
    }

    #close-controls {
        width: 100%;
        margin-top: 1;
    }

    #status-card {
        height: auto;
        max-height: 9;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("1", "shortcut_1", "CPU"),
        Binding("2", "shortcut_2", "Power"),
        Binding("3", "shortcut_3", "Profile"),
        Binding("4", "shortcut_4", "Curve"),
        Binding("5", "shortcut_5", "Quick"),
        Binding("b", "back", "Back", show=False),
        Binding("escape", "back", "Back", show=False),
        Binding("q", "quit_app", "Quit"),
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
    FAN_PROFILES = {"1": "Performance", "2": "Balanced", "3": "Quiet"}
    FAN_CURVES = {"1": "aggressive", "2": "max"}
    QUICK_PRESETS = {
        "1": ("Default", 2500000, "silent", "Balanced", "aggressive"),
        "2": ("Balanced", 3500000, "balanced", "Balanced", "aggressive"),
        "3": ("Performance", 4000000, "performance", "Performance", "max"),
    }

    def __init__(self, collector: DataCollector | None = None) -> None:
        super().__init__()
        self.state = getattr(collector, "state", AppState())
        self.collector = collector or DataCollector(self.state)
        self.active_control_panel: str | None = None
        self.running_action: ControlAction | None = None
        self._action_thread: threading.Thread | None = None
        self.actions = self._build_actions()
        self.actions_by_panel: dict[str, list[ControlAction]] = defaultdict(list)
        self.actions_by_key: dict[str, dict[str, ControlAction]] = defaultdict(dict)
        self.actions_by_button_id: dict[str, ControlAction] = {}
        for action in self.actions:
            self.actions_by_panel[action.panel].append(action)
            self.actions_by_key[action.panel][action.key] = action

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="content"):
            with VerticalScroll(id="dashboard"):
                yield Static(id="header-card")
                with Horizontal(classes="dashboard-row"):
                    yield Static(id="cpu-card", classes="metric-card")
                    yield Static(id="cooling-card", classes="metric-card")
                with Horizontal(classes="dashboard-row"):
                    yield Static(id="amd-gpu-card", classes="metric-card")
                    yield Static(id="nvidia-card", classes="metric-card")
                with Horizontal(classes="dashboard-row"):
                    yield Static(id="power-card", classes="metric-card")
                    yield Static(id="battery-card", classes="metric-card")
            with VerticalScroll(id="controls"):
                yield Label("Controls", id="control-title")
                with Horizontal(id="control-tabs"):
                    yield Button("CPU", id="tab-cpu")
                    yield Button("Power", id="tab-power")
                    yield Button("Fans", id="tab-fan-profile")
                    yield Button("Curve", id="tab-fan-curve")
                    yield Button("Quick", id="tab-quick")
                for panel in PANEL_ORDER:
                    with Vertical(id=f"{PANEL_DOM_IDS[panel]}-section", classes="control-section"):
                        yield Label(PANEL_TITLES[panel], classes="section-heading")
                        for action in self.actions_by_panel[panel]:
                            button_id = self._button_id(action)
                            self.actions_by_button_id[button_id] = action
                            yield Button(
                                f"{action.key}  {action.label}",
                                id=button_id,
                                classes="action-button",
                                variant=self._button_variant(action),
                            )
                            yield Static(action.description, classes="action-detail")
                yield Button("Close", id="close-controls")
        yield Static(id="status-card")
        yield Footer()

    def on_mount(self) -> None:
        self.collector.start()
        self.query_one("#controls", VerticalScroll).display = False
        for panel in PANEL_ORDER:
            self.query_one(f"#{PANEL_DOM_IDS[panel]}-section", Vertical).display = False
        self.set_interval(0.5, self.refresh_dashboard)
        self.refresh_dashboard()

    def on_unmount(self) -> None:
        self.collector.stop()

    def refresh_dashboard(self) -> None:
        state = self.collector.current_state()
        self.query_one("#header-card", Static).update(self._render_header(state))
        self.query_one("#cpu-card", Static).update(self._render_cpu_panel(state))
        self.query_one("#cooling-card", Static).update(self._render_cooling_panel(state))
        self.query_one("#amd-gpu-card", Static).update(self._render_amd_gpu_panel(state))
        self.query_one("#nvidia-card", Static).update(self._render_nvidia_panel(state))
        self.query_one("#power-card", Static).update(self._render_power_panel(state))
        self.query_one("#battery-card", Static).update(self._render_battery_panel(state))
        self.query_one("#status-card", Static).update(self._render_status(state))
        self._sync_button_states(state)

    @on(Button.Pressed)
    def _button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "close-controls":
            self._show_controls(None)
            return
        if button_id.startswith("tab-"):
            panel = button_id.removeprefix("tab-").replace("-", "_")
            if panel in PANEL_TITLES:
                self._show_controls(panel)
            return
        action = self.actions_by_button_id.get(button_id)
        if action is not None:
            self._request_action(action)

    def on_key(self, event) -> None:
        if self.active_control_panel is None:
            return
        action = self.actions_by_key[self.active_control_panel].get(event.key.lower())
        if action is None:
            return
        event.stop()
        self._request_action(action)

    def action_shortcut_1(self) -> None:
        self._handle_shortcut("1")

    def action_shortcut_2(self) -> None:
        self._handle_shortcut("2")

    def action_shortcut_3(self) -> None:
        self._handle_shortcut("3")

    def action_shortcut_4(self) -> None:
        self._handle_shortcut("4")

    def action_shortcut_5(self) -> None:
        self._handle_shortcut("5")

    def action_back(self) -> None:
        if self.active_control_panel is not None:
            self._show_controls(None)
        else:
            self.exit()

    def action_quit_app(self) -> None:
        self.exit()

    def _handle_shortcut(self, key: str) -> None:
        if self.active_control_panel is not None:
            action = self.actions_by_key[self.active_control_panel].get(key)
            if action is not None:
                self._request_action(action)
            return
        panel = {"1": "cpu", "2": "power", "3": "fan_profile", "4": "fan_curve", "5": "quick"}[key]
        self._show_controls(panel)

    def _show_controls(self, panel: str | None) -> None:
        self.active_control_panel = panel
        self.query_one("#controls", VerticalScroll).display = panel is not None
        for item in PANEL_ORDER:
            self.query_one(f"#{PANEL_DOM_IDS[item]}-section", Vertical).display = item == panel
        title = "Controls" if panel is None else PANEL_TITLES[panel]
        self.query_one("#control-title", Label).update(title)
        if panel is not None:
            first_action = next(iter(self.actions_by_panel[panel]), None)
            if first_action is not None:
                self.query_one(f"#{self._button_id(first_action)}", Button).focus()

    def _request_action(self, action: ControlAction) -> None:
        if self.running_action is not None:
            self.collector.update_message(f"Still running: {self.running_action.label}", "yellow")
            self.refresh_dashboard()
            return
        if not self._action_available(action, self.collector.current_state()):
            self.collector.update_message(f"Unavailable: {action.label}", "yellow")
            self.refresh_dashboard()
            return
        if action.confirmation:
            self.push_screen(ConfirmScreen(action.confirmation), lambda confirmed: self._confirmed_action(action, confirmed))
            return
        self._start_action(action)

    def _confirmed_action(self, action: ControlAction, confirmed: bool) -> None:
        if confirmed:
            self._start_action(action)
        else:
            self.collector.update_message("Cancelled.", "yellow")
            self.refresh_dashboard()

    def _start_action(self, action: ControlAction) -> None:
        self.running_action = action
        self.collector.update_message(f"Running: {action.label}", "yellow")
        self.refresh_dashboard()
        self._action_thread = threading.Thread(
            target=self._run_control_action,
            args=(action,),
            daemon=True,
            name=f"rog-control-action-{action.id}",
        )
        self._action_thread.start()

    def _run_control_action(self, action: ControlAction) -> None:
        try:
            success, message = execute_control_action(action, self.collector)
        except Exception as exc:
            logger.exception("Control action failed")
            success, message = False, f"{action.label} failed: {exc}"
        try:
            self.call_from_thread(self._finish_action, action, success, message)
        except RuntimeError:
            logger.debug("Skipped action completion because the app is no longer running")

    def _finish_action(self, action: ControlAction, success: bool, message: str) -> None:
        self.running_action = None
        self.collector.update_message(message, "green" if success else "red")
        if success:
            self._show_controls(None)
        self.refresh_dashboard()

    def _sync_button_states(self, state: AppState) -> None:
        for action in self.actions:
            button = self.query_one(f"#{self._button_id(action)}", Button)
            button.disabled = self.running_action is not None or not self._action_available(action, state)

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
                    description=f"Set max CPU frequency to {freq / 1_000_000:.2f} GHz.",
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
                    description=f"Apply RyzenAdj limits with {watts}W STAPM.",
                    kind="power_preset",
                    payload={"preset": preset_name},
                    capabilities=("power",),
                    confirmation=confirmation,
                )
            )

        for key, profile in self.FAN_PROFILES.items():
            actions.append(
                ControlAction(
                    id=f"fan-profile-{key}",
                    panel="fan_profile",
                    key=key,
                    label=profile,
                    description="Apply ASUS profile behavior for this mode.",
                    kind="fan_profile",
                    payload={"profile": profile},
                    capabilities=("fan",),
                )
            )

        for key, preset in self.FAN_CURVES.items():
            confirmation = "Set fans to 100%?" if preset == "max" else None
            actions.append(
                ControlAction(
                    id=f"fan-curve-{key}",
                    panel="fan_curve",
                    key=key,
                    label=preset.replace("_", " ").title(),
                    description="Apply this curve to the current ASUS fan profile.",
                    kind="fan_curve",
                    payload={"preset": preset},
                    capabilities=("fan",),
                    confirmation=confirmation,
                )
            )
        actions.append(
            ControlAction(
                id="fan-curve-reset",
                panel="fan_curve",
                key="d",
                label="Firmware defaults",
                description="Reset fan curves and return control to firmware.",
                kind="fan_reset",
                payload={},
                capabilities=("fan",),
            )
        )

        for key, preset in self.QUICK_PRESETS.items():
            name, freq, power_preset, fan_profile, fan_curve = preset
            confirmation = None
            if name == "Performance":
                confirmation = "Apply Performance preset (55W plus max fans)?"
            actions.append(
                ControlAction(
                    id=f"quick-{key}",
                    panel="quick",
                    key=key,
                    label=name,
                    description=f"{freq / 1_000_000:.2f} GHz, {power_preset}, {fan_profile}, {fan_curve}.",
                    kind="quick_preset",
                    payload={
                        "name": name,
                        "freq": freq,
                        "power": power_preset,
                        "fan_profile": fan_profile,
                        "fan_curve": fan_curve,
                    },
                    capabilities=("cpu", "power", "fan"),
                    confirmation=confirmation,
                )
            )
        return actions

    @staticmethod
    def _button_id(action: ControlAction) -> str:
        return f"action-{action.id}"

    @staticmethod
    def _button_variant(action: ControlAction) -> str:
        if action.confirmation:
            return "warning"
        if action.panel == "quick":
            return "success"
        return "primary"

    def _render_header(self, state: AppState) -> Panel:
        snapshot = state.snapshot
        title = Text("ROG Control", style="bold green")
        subtitle = Text("System Monitoring and Controls", style="dim")
        badges = [
            _capability_badge(snapshot.capabilities.get("cpu_hwmon", Capability(False, "unknown")), "CPU"),
            _capability_badge(snapshot.capabilities.get("amd_hwmon", Capability(False, "unknown")), "AMD GPU"),
            _capability_badge(snapshot.capabilities.get("nvidia", Capability(False, "unknown")), "NVIDIA"),
            _capability_badge(state.power_capability, "RyzenAdj", state.power_error),
            _capability_badge(state.fan_capability, "asusctl", state.fan_error),
        ]
        return Panel(
            Group(Align.center(title), Align.center(subtitle), Columns(badges, expand=True)),
            border_style="green",
        )

    def _metric_table(self, title: str, rows: list[tuple[str, str | Text]], border: str = "green") -> Panel:
        table = Table.grid(expand=True)
        table.add_column(style="bold white", ratio=1)
        table.add_column(justify="right", ratio=1)
        for label, value in rows:
            table.add_row(label, value)
        return Panel(table, title=title, border_style=border)

    def _render_cpu_panel(self, state: AppState) -> Panel:
        cpu = state.snapshot.cpu
        rows = [
            ("Temperature", fmt_temp(cpu.temp_c)),
            ("Current", fmt_freq(cpu.current_freq_mhz)),
            ("Limit", fmt_freq(cpu.max_freq_mhz)),
            ("Governor", cpu.governor or "Unavailable"),
            ("Trend", sparkline(state.cpu_temp_history)),
        ]
        return self._metric_table("CPU", rows, border=self._temp_border(cpu.temp_c))

    def _render_cooling_panel(self, state: AppState) -> Panel:
        cooling = state.snapshot.cooling
        fan_status = "Enabled" if state.custom_curve_enabled else "Disabled"
        if state.custom_curve_enabled is None:
            fan_status = "Unavailable"
        rows = [
            ("CPU Fan", fmt_rpm(cooling.cpu_fan_rpm)),
            ("GPU Fan", fmt_rpm(cooling.gpu_fan_rpm)),
            ("Profile", state.fan_profile or "Unavailable"),
            ("Custom Curve", fan_status),
            ("NVMe Temp", fmt_temp(state.snapshot.nvme_temp_c)),
        ]
        panel = self._metric_table("Cooling", rows, border=self._temp_border(state.snapshot.nvme_temp_c))
        if state.fan_capability.available and not state.fan_error:
            return panel
        details = state.fan_error or state.fan_capability.reason
        return Panel(Group(panel.renderable, Text(details, style="yellow")), title="Cooling", border_style="yellow")

    def _render_amd_gpu_panel(self, state: AppState) -> Panel:
        gpu = state.snapshot.amd_gpu
        capability = state.snapshot.capabilities.get("amd_hwmon", Capability(False, "AMD GPU telemetry unavailable"))
        rows = [
            ("Temperature", fmt_temp(gpu.temp_c)),
            ("Clock", f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else "Unavailable"),
            ("Power", fmt_power(gpu.power_w)),
            ("Trend", sparkline(state.amd_gpu_temp_history)),
        ]
        panel = self._metric_table("AMD iGPU", rows, border=self._temp_border(gpu.temp_c))
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")), title="AMD iGPU", border_style="yellow")

    def _render_nvidia_panel(self, state: AppState) -> Panel:
        gpu = state.snapshot.nvidia_gpu
        capability = state.snapshot.capabilities.get("nvidia", Capability(False, "NVIDIA telemetry unavailable"))
        vram = "Unavailable"
        if gpu.vram_used_mb is not None and gpu.vram_total_mb is not None:
            vram = f"{gpu.vram_used_mb}/{gpu.vram_total_mb} MB"
        rows = [
            ("Temperature", fmt_temp(gpu.temp_c)),
            ("Clock", f"{gpu.clock_mhz} MHz" if gpu.clock_mhz is not None else "Unavailable"),
            ("Power", fmt_power(gpu.power_w)),
            ("Utilization", fmt_percent(gpu.util_percent)),
            ("VRAM", vram),
        ]
        panel = self._metric_table("NVIDIA dGPU", rows, border=self._temp_border(gpu.temp_c))
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")), title="NVIDIA dGPU", border_style="yellow")

    def _render_power_panel(self, state: AppState) -> Panel:
        info = state.power_info
        rows = [
            ("STAPM", limit_str(info.stapm_value, info.stapm_limit)),
            ("Fast PPT", limit_str(info.fast_value, info.fast_limit)),
            ("Slow PPT", limit_str(info.slow_value, info.slow_limit)),
            ("Thermal", limit_str(info.tctl_value, info.tctl_limit, unit="C")),
        ]
        panel = self._metric_table("Power", rows, border=self._ratio_border(info.stapm_value, info.stapm_limit))
        if state.power_capability.available and not state.power_error:
            return panel
        details = state.power_error or state.power_capability.reason
        return Panel(Group(panel.renderable, Text(details, style="yellow")), title="Power", border_style="yellow")

    def _render_battery_panel(self, state: AppState) -> Panel:
        battery = state.snapshot.battery
        capability = state.snapshot.capabilities.get("battery", Capability(False, "Battery unavailable"))
        rows = [
            ("Charge", fmt_percent(battery.percent)),
            ("Status", battery.status or "Unavailable"),
            ("Power", fmt_power(battery.power_w)),
        ]
        panel = self._metric_table("Battery & Status", rows, border=self._battery_border(battery.percent))
        if capability.available:
            return panel
        return Panel(Group(panel.renderable, Text(capability.reason, style="yellow")), title="Battery & Status", border_style="yellow")

    def _render_status(self, state: AppState) -> RenderableType:
        cpu_status = fmt_freq(state.snapshot.cpu.max_freq_mhz) if state.snapshot.cpu.max_freq_mhz is not None else "---"
        power_status = f"{state.power_info.stapm_limit:.0f}W" if state.power_info.stapm_limit is not None else "---"
        lines: list[RenderableType] = [
            Text(state.message, style=state.message_style),
            Text.from_markup(
                f"[dim]CPU cap:[/] {cpu_status}  [dim]Power:[/] {power_status}  [dim]Fan:[/] {state.fan_profile or '---'}"
            ),
        ]
        if self.running_action is not None:
            lines.append(Text(f"Running action: {self.running_action.label}", style="yellow"))
        if state.errors:
            error_text = Text("\n".join(state.errors[:4]), style="yellow")
            lines.append(error_text)
        border = "yellow" if state.errors else "green"
        return Panel(Group(*lines), title="Status", border_style=border)

    @staticmethod
    def _temp_border(temp: float | None) -> str:
        if temp is None:
            return "green"
        if temp >= 90:
            return "red"
        if temp >= 85:
            return "orange1"
        if temp >= 70:
            return "yellow"
        return "green"

    @staticmethod
    def _ratio_border(value: float | None, limit: float | None) -> str:
        if value is None or limit is None or limit <= 0:
            return "green"
        ratio = value / limit
        if ratio >= 0.95:
            return "red"
        if ratio >= 0.85:
            return "orange1"
        if ratio >= 0.70:
            return "yellow"
        return "green"

    @staticmethod
    def _battery_border(percent: int | None) -> str:
        if percent is None:
            return "green"
        if percent < 20:
            return "red"
        if percent < 50:
            return "yellow"
        return "green"
