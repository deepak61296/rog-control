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


def test_keyboard_shortcut_opens_controls_and_runs_action() -> None:
    asyncio.run(_run_keyboard_shortcut())


async def _run_keyboard_shortcut() -> None:
    collector = FakeCollector()
    app = RogControlApp(collector=collector)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("1")
        await pilot.pause(0.2)
        assert collector.cpu.calls == [2500000]
        assert app.active_control_panel == "cpu"

    assert collector.started
    assert collector.stopped
