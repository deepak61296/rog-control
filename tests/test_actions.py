from __future__ import annotations

from types import SimpleNamespace

from src.ui.actions import ControlAction, execute_control_action


class FakeCPU:
    def __init__(self, result: tuple[bool, str] = (True, "cpu ok")) -> None:
        self.result = result
        self.calls: list[int] = []

    def set_max_freq_all(self, freq: int) -> tuple[bool, str]:
        self.calls.append(freq)
        return self.result


class FakePower:
    def __init__(self, result: tuple[bool, str] = (True, "power ok")) -> None:
        self.result = result
        self.calls: list[str] = []

    def set_preset(self, preset: str) -> tuple[bool, str]:
        self.calls.append(preset)
        return self.result


class FakeFans:
    def __init__(self, result: tuple[bool, str] = (True, "fan ok")) -> None:
        self.result = result
        self.calls: list[tuple] = []

    def apply_profile_behavior(self, profile: str) -> tuple[bool, str]:
        self.calls.append(("apply_profile_behavior", profile))
        return self.result

    def set_profile(self, profile: str) -> tuple[bool, str]:
        self.calls.append(("set_profile", profile))
        return self.result

    def set_fan_curve_preset(self, preset: str, profile: str) -> tuple[bool, str]:
        self.calls.append(("set_fan_curve_preset", preset, profile))
        return self.result

    def enable_custom_curves(self, profile: str, enable: bool = True) -> tuple[bool, str]:
        self.calls.append(("enable_custom_curves", profile, enable))
        return self.result

    def reset_fan_curve(self, profile: str) -> tuple[bool, str]:
        self.calls.append(("reset_fan_curve", profile))
        return self.result


class FakeCollector:
    def __init__(
        self,
        cpu: FakeCPU | None = None,
        power: FakePower | None = None,
        fans: FakeFans | None = None,
        fan_profile: str | None = "Balanced",
    ) -> None:
        self.cpu = cpu or FakeCPU()
        self.power = power or FakePower()
        self.fans = fans or FakeFans()
        self.fan_profile = fan_profile

    def current_state(self):
        return SimpleNamespace(fan_profile=self.fan_profile)


def test_cpu_frequency_action_calls_cpu_controller() -> None:
    collector = FakeCollector()
    action = ControlAction(
        id="cpu-1",
        panel="cpu",
        key="1",
        label="Silent cap",
        description="",
        kind="cpu_freq",
        payload={"freq": 2500000},
        capabilities=("cpu",),
    )

    assert execute_control_action(action, collector) == (True, "cpu ok")
    assert collector.cpu.calls == [2500000]


def test_fan_curve_uses_current_profile_and_enables_custom_curves() -> None:
    collector = FakeCollector(fan_profile="Quiet")
    action = ControlAction(
        id="fan-curve-1",
        panel="fan_curve",
        key="1",
        label="Aggressive",
        description="",
        kind="fan_curve",
        payload={"preset": "aggressive"},
        capabilities=("fan",),
    )

    assert execute_control_action(action, collector) == (True, "fan ok")
    assert collector.fans.calls == [
        ("set_fan_curve_preset", "aggressive", "Quiet"),
        ("enable_custom_curves", "Quiet", True),
    ]


def test_quick_preset_stops_on_first_failure() -> None:
    collector = FakeCollector(power=FakePower((False, "no power")))
    action = ControlAction(
        id="quick-1",
        panel="quick",
        key="1",
        label="Default",
        description="",
        kind="quick_preset",
        payload={
            "name": "Default",
            "freq": 2500000,
            "power": "silent",
            "fan_profile": "Balanced",
            "fan_curve": "aggressive",
        },
        capabilities=("cpu", "power", "fan"),
    )

    success, message = execute_control_action(action, collector)

    assert not success
    assert message == "Power preset: no power"
    assert collector.cpu.calls == [2500000]
    assert collector.power.calls == ["silent"]
    assert collector.fans.calls == []
