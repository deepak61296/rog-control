from __future__ import annotations

import asyncio

from src.core.sensors import Capability
from src.ui.app import RogControlApp
from src.ui.state import AppState


class FakeCPU:
    capability = Capability(True)
    last_error = ""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def set_max_freq_all(self, freq: int) -> tuple[bool, str]:
        self.calls.append(freq)
        return True, "CPU frequency limit updated"


class FakePower:
    capability = Capability(True)
    last_error = ""
    POWER_PRESETS = {
        "silent": {"stapm": 15000},
        "eco": {"stapm": 25000},
        "cool": {"stapm": 35000},
        "balanced": {"stapm": 45000},
        "performance": {"stapm": 55000},
        "high": {"stapm": 65000},
    }


class FakeFans:
    capability = Capability(True)
    last_error = ""


class FakeCollector:
    def __init__(self) -> None:
        self.state = AppState(
            cpu_capability=Capability(True),
            power_capability=Capability(True),
            fan_capability=Capability(True),
        )
        self.cpu = FakeCPU()
        self.power = FakePower()
        self.fans = FakeFans()
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def current_state(self) -> AppState:
        return self.state

    def update_message(self, message: str, style: str = "cyan") -> None:
        self.state.message = message
        self.state.message_style = style


def test_keyboard_shortcut_selects_tab_without_running_action() -> None:
    asyncio.run(_run_keyboard_shortcut())


async def _run_keyboard_shortcut() -> None:
    collector = FakeCollector()
    app = RogControlApp(collector=collector)
    assert not app.ENABLE_COMMAND_PALETTE

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("2")
        await pilot.pause(0.1)
        assert app.active_control_panel == "power"

        await pilot.press("3")
        await pilot.pause(0.1)
        assert app.active_control_panel == "fans"
        fan_labels = [action.label for action in app.actions_by_panel["fans"]]
        assert fan_labels == ["Aggressive", "Max", "Firmware Default"]

        await pilot.press("4")
        await pilot.pause(0.1)
        assert app.active_control_panel == "quick"
        quick_labels = [action.label for action in app.actions_by_panel["quick"]]
        assert quick_labels == [
            "Ultra Battery Saver",
            "Battery Saver",
            "Battery Performance",
            "PD Productivity",
            "OEM Performance",
        ]
        assert app.actions_by_panel["quick"][-1].confirmation == (
            "Apply OEM Performance (30W with max fans)? Use only with the 240W ASUS adapter."
        )

        await pilot.press("1")
        await pilot.pause(0.1)
        assert collector.cpu.calls == []
        assert app.active_control_panel == "cpu"

    assert collector.started
    assert collector.stopped


def test_successful_action_message_uses_status_bar_not_notification() -> None:
    asyncio.run(_run_successful_action_message())


async def _run_successful_action_message() -> None:
    collector = FakeCollector()
    app = RogControlApp(collector=collector)
    notifications: list[tuple[str, str | None]] = []

    def fake_notify(message: str, *args, **kwargs) -> None:
        notifications.append((message, kwargs.get("severity")))

    async with app.run_test(size=(120, 40)) as pilot:
        app.notify = fake_notify
        action = app.actions_by_panel["fans"][0]
        app._finish_action(action, True, "Custom fan curves enabled; not saved for reboot because sudo is not available")
        await pilot.pause(0.1)

        assert notifications == []
        assert "not saved for reboot" in collector.state.message
