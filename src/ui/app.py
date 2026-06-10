"""Modern Textual TUI for ROG Control."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Grid
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Static, Sparkline, TabbedContent, TabPane, Markdown

from src.core.sensors import Capability
from src.ui.actions import ControlAction, execute_control_action
from src.ui.collector import DataCollector
from src.ui.state import AppState

logger = logging.getLogger(__name__)

PANEL_TITLES = {
    "cpu": "CPU",
    "power": "Power",
    "fan_profile": "Fans",
    "fan_curve": "Curve",
    "quick": "Quick",
}
PANEL_ORDER = ("cpu", "power", "fan_profile", "fan_curve", "quick")


class MetricRow(Static):
    """A row containing a label on the left and a reactive value on the right."""
    
    value = reactive("---")

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.label_text = label
        self._value_label = Label(self.value, classes="metric-value")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="metric-row"):
            yield Label(self.label_text, classes="metric-label")
            yield self._value_label

    def watch_value(self, value: str) -> None:
        if hasattr(self, "_value_label"):
            self._value_label.update(value)


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


class CPUDashboard(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("CPU", classes="card-title")
            self.temp = MetricRow("Temperature")
            yield self.temp
            self.freq = MetricRow("Current Freq")
            yield self.freq
            self.limit = MetricRow("Limit Freq")
            yield self.limit
            self.power = MetricRow("Package Power")
            yield self.power
            self.governor = MetricRow("Governor")
            yield self.governor
            yield Label("Utilization %", classes="graph-title")
            self.sparkline = Sparkline(summary_function=max)
            yield self.sparkline

    def update_state(self, state: AppState) -> None:
        cpu = state.snapshot.cpu
        temp = cpu.temp_c
        self.temp.value = f"{temp:.0f} °C" if temp is not None else "---"
        freq = cpu.current_freq_mhz
        self.freq.value = f"{freq / 1000:.2f} GHz" if freq is not None else "---"
        limit = cpu.max_freq_mhz
        self.limit.value = f"{limit / 1000:.2f} GHz" if limit is not None else "---"
        
        power = state.power_info.stapm_value
        self.power.value = f"{power:.1f} W" if power is not None else "---"
        self.governor.value = cpu.governor or "---"

        if state.cpu_util_history:
            self.sparkline.data = state.cpu_util_history


class GPUDashboard(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("NVIDIA dGPU", classes="card-title")
            self.temp = MetricRow("Temperature")
            yield self.temp
            self.clock = MetricRow("Clock")
            yield self.clock
            self.power = MetricRow("Power")
            yield self.power
            self.vram = MetricRow("VRAM")
            yield self.vram
            yield Label("Utilization %", classes="graph-title")
            self.sparkline = Sparkline(summary_function=max)
            yield self.sparkline

    def update_state(self, state: AppState) -> None:
        gpu = state.snapshot.nvidia_gpu
        temp = gpu.temp_c
        self.temp.value = f"{temp:.0f} °C" if temp is not None else "---"
        clock = gpu.clock_mhz
        self.clock.value = f"{clock} MHz" if clock is not None else "---"
        power = gpu.power_w
        self.power.value = f"{power:.1f} W" if power is not None else "---"
        
        if gpu.vram_used_mb is not None and gpu.vram_total_mb is not None:
            self.vram.value = f"{gpu.vram_used_mb}/{gpu.vram_total_mb} MB"
        else:
            self.vram.value = "---"

        if state.gpu_util_history:
            self.sparkline.data = state.gpu_util_history


class PowerDashboard(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Power Limits", classes="card-title")
            self.stapm = MetricRow("STAPM (Sustained)")
            yield self.stapm
            self.fast = MetricRow("Fast PPT (Boost)")
            yield self.fast
            self.slow = MetricRow("Slow PPT (Long)")
            yield self.slow
            self.tctl = MetricRow("Thermal Target")
            yield self.tctl

    def update_state(self, state: AppState) -> None:
        info = state.power_info
        
        def fmt(val: float | None, lim: float | None, unit: str = "W") -> str:
            v = f"{val:.1f}" if val is not None else "---"
            l = f"{lim:.0f}" if lim is not None else "---"
            return f"{v} / {l} {unit}"

        self.stapm.value = fmt(info.stapm_value, info.stapm_limit)
        self.fast.value = fmt(info.fast_value, info.fast_limit)
        self.slow.value = fmt(info.slow_value, info.slow_limit)
        self.tctl.value = fmt(info.tctl_value, info.tctl_limit, "°C")


class CoolingDashboard(Static):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Cooling", classes="card-title")
            self.cpu_fan = MetricRow("CPU Fan")
            yield self.cpu_fan
            self.gpu_fan = MetricRow("GPU Fan")
            yield self.gpu_fan
            self.profile = MetricRow("Active Profile")
            yield self.profile
            self.curve = MetricRow("Custom Curve")
            yield self.curve

    def update_state(self, state: AppState) -> None:
        cooling = state.snapshot.cooling
        self.cpu_fan.value = f"{cooling.cpu_fan_rpm} RPM" if cooling.cpu_fan_rpm else "---"
        self.gpu_fan.value = f"{cooling.gpu_fan_rpm} RPM" if cooling.gpu_fan_rpm else "---"
        self.profile.value = state.fan_profile or "---"
        
        if state.custom_curve_enabled is None:
            self.curve.value = "---"
        else:
            self.curve.value = "Enabled" if state.custom_curve_enabled else "Disabled"


class RogControlApp(App[None]):
    """Main Textual application."""

    TITLE = "ROG Control"

    CSS = """
    $primary: #39ff14;
    $secondary: #ff0033;
    $success: #39ff14;
    $warning: #ff0033;
    $surface: #110505;
    $background: #050000;
    $text-muted: #8b949e;

    Screen {
        layout: vertical;
        background: $background;
    }

    #main-grid {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 2fr 1fr;
        height: 1fr;
    }

    .dashboard-pane {
        layout: grid;
        grid-size: 2 2;
        padding: 1 2;
        grid-gutter: 1 2;
        overflow-y: auto;
    }

    .control-pane {
        border-left: vkey #30363d;
        background: $surface;
        padding: 0 1;
        overflow-y: auto;
    }

    .card {
        border: round $primary;
        background: #0d1117;
        padding: 0 1;
        height: 100%;
        min-height: 12;
    }

    .card-title {
        text-style: bold;
        color: $primary;
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        border-bottom: solid $primary;
    }
    
    .graph-title {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }

    .metric-row {
        layout: horizontal;
        height: auto;
    }

    .metric-label {
        width: 1fr;
        color: $text-muted;
    }

    .metric-value {
        width: 1fr;
        text-align: right;
        text-style: bold;
    }

    Sparkline {
        height: 1fr;
        min-height: 3;
        margin-top: 1;
    }

    Sparkline > .sparkline--max-color {
        color: $secondary;
    }

    Sparkline > .sparkline--min-color {
        color: $success;
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
        Binding("3", "shortcut_3", "Profile"),
        Binding("4", "shortcut_4", "Curve"),
        Binding("5", "shortcut_5", "Quick"),
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
        self.running_action: ControlAction | None = None
        self.actions = self._build_actions()
        
        self.actions_by_panel: dict[str, list[ControlAction]] = defaultdict(list)
        self.actions_by_key: dict[str, dict[str, ControlAction]] = defaultdict(dict)
        self.actions_by_button_id: dict[str, ControlAction] = {}
        for action in self.actions:
            self.actions_by_panel[action.panel].append(action)
            self.actions_by_key[action.panel][action.key] = action
            
        self.active_control_panel: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal(id="main-grid"):
            with Grid(classes="dashboard-pane"):
                self.cpu_card = CPUDashboard(classes="card")
                yield self.cpu_card
                self.gpu_card = GPUDashboard(classes="card")
                yield self.gpu_card
                self.power_card = PowerDashboard(classes="card")
                yield self.power_card
                self.cooling_card = CoolingDashboard(classes="card")
                yield self.cooling_card

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
        self.collector.start()
        self.set_interval(0.5, self.refresh_dashboard)
        self.refresh_dashboard()

    def on_unmount(self) -> None:
        self.collector.stop()

    def refresh_dashboard(self) -> None:
        state = self.collector.current_state()
        self.cpu_card.update_state(state)
        self.gpu_card.update_state(state)
        self.power_card.update_state(state)
        self.cooling_card.update_state(state)

        for action in self.actions:
            button = self.query_one(f"#action-{action.id}", Button)
            button.disabled = self.running_action is not None or not self._action_available(action, state)
            
        if self.running_action:
            self.status_bar.update(f"Running action: {self.running_action.label}...")
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
    def action_shortcut_5(self) -> None: self._handle_shortcut("5")

    def action_back(self) -> None:
        if self.active_control_panel is not None:
            self.active_control_panel = None
            self.notify("Controls unfocused. Press 1-5 to select a panel.", severity="information")
        else:
            self.exit()

    @on(TabbedContent.TabActivated)
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane.id and event.pane.id.startswith("tab-"):
            self.active_control_panel = event.pane.id.replace("tab-", "")

    def _handle_shortcut(self, key: str) -> None:
        if self.active_control_panel is not None:
            action = self.actions_by_key[self.active_control_panel].get(key)
            if action is not None:
                self._request_action(action)
            return
        panel = {"1": "cpu", "2": "power", "3": "fan_profile", "4": "fan_curve", "5": "quick"}[key]
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
        self.notify(message, severity="information" if success else "error")
        self.refresh_dashboard()

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

        for key, profile in self.FAN_PROFILES.items():
            actions.append(
                ControlAction(
                    id=f"fan-profile-{key}",
                    panel="fan_profile",
                    key=key,
                    label=profile,
                    description=f"Apply {profile} profile.",
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
                panel="fan_curve",
                key="d",
                label="Firmware defaults",
                description="Reset to firmware fan control.",
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
                    description=f"{freq / 1_000_000:.2f} GHz, {power_preset}, {fan_profile}.",
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
