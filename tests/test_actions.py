from __future__ import annotations

from types import SimpleNamespace

from src.ui.actions import ControlAction, execute_control_action


def install_profile_spy(monkeypatch):
    saves = []

    def fake_save_profile(updates):
        saves.append(dict(updates))
        return True, "Profile saved"

    monkeypatch.setattr("src.ui.actions._save_profile", fake_save_profile)
    return saves


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


def test_cpu_frequency_action_calls_cpu_controller(monkeypatch) -> None:
    saves = install_profile_spy(monkeypatch)
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
    assert saves == [{"cpu_freq": 2500000}]


def test_fan_curve_uses_current_profile_and_enables_custom_curves(monkeypatch) -> None:
    saves = install_profile_spy(monkeypatch)
    collector = FakeCollector(fan_profile="Quiet")
    action = ControlAction(
        id="fan-curve-1",
        panel="fans",
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
    assert saves == [{"fan_curve": "aggressive", "fan_profile": "Quiet"}]


def test_quick_preset_stops_on_first_failure(monkeypatch) -> None:
    saves = install_profile_spy(monkeypatch)
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
            "fan_mode": "firmware",
        },
        capabilities=("cpu", "power", "fan"),
    )

    success, message = execute_control_action(action, collector)

    assert not success
    assert message == "Power preset: no power"
    assert collector.cpu.calls == [2500000]
    assert collector.power.calls == ["silent"]
    assert collector.fans.calls == []
    assert saves == [{"cpu_freq": 2500000}]


def test_quick_ultra_battery_saver_restores_firmware_fans_and_saves_profile(monkeypatch) -> None:
    saves = install_profile_spy(monkeypatch)
    collector = FakeCollector()
    action = ControlAction(
        id="quick-1",
        panel="quick",
        key="1",
        label="Ultra Battery Saver",
        description="",
        kind="quick_preset",
        payload={
            "name": "Ultra Battery Saver",
            "freq": 1500000,
            "power": "silent",
            "fan_profile": "Quiet",
            "fan_mode": "firmware",
        },
        capabilities=("cpu", "power", "fan"),
    )

    assert execute_control_action(action, collector) == (True, "Applied preset: Ultra Battery Saver")
    assert collector.cpu.calls == [1500000]
    assert collector.power.calls == ["silent"]
    assert collector.fans.calls == [
        ("set_profile", "Quiet"),
        ("reset_fan_curve", "Quiet"),
        ("enable_custom_curves", "Quiet", False),
    ]
    assert saves == [
        {
            "cpu_freq": 1500000,
            "power_preset": "silent",
            "fan_profile": "Quiet",
            "fan_reset": True,
        }
    ]


def test_quick_oem_performance_uses_max_fans_and_saves_profile(monkeypatch) -> None:
    saves = install_profile_spy(monkeypatch)
    collector = FakeCollector()
    action = ControlAction(
        id="quick-5",
        panel="quick",
        key="5",
        label="OEM Performance",
        description="",
        kind="quick_preset",
        payload={
            "name": "OEM Performance",
            "freq": 3000000,
            "power": "ac",
            "fan_profile": "Performance",
            "fan_mode": "max",
        },
        capabilities=("cpu", "power", "fan"),
    )

    assert execute_control_action(action, collector) == (True, "Applied preset: OEM Performance")
    assert collector.cpu.calls == [3000000]
    assert collector.power.calls == ["ac"]
    assert collector.fans.calls == [
        ("set_profile", "Performance"),
        ("set_fan_curve_preset", "max", "Performance"),
        ("enable_custom_curves", "Performance", True),
    ]
    assert saves == [
        {
            "cpu_freq": 3000000,
            "power_preset": "ac",
            "fan_profile": "Performance",
            "fan_curve": "max",
        }
    ]


def test_successful_action_is_not_failed_when_profile_save_needs_sudo(monkeypatch) -> None:
    def fake_save_profile(updates):
        return False, "sudo: a password is required"

    monkeypatch.setattr("src.ui.actions._save_profile", fake_save_profile)
    collector = FakeCollector()
    action = ControlAction(
        id="fan-curve-1",
        panel="fans",
        key="1",
        label="Aggressive",
        description="",
        kind="fan_curve",
        payload={"preset": "aggressive"},
        capabilities=("fan",),
    )

    success, message = execute_control_action(action, collector)

    assert success
    assert message == "fan ok; not saved for reboot because sudo is not available"
