from __future__ import annotations

from src.core.profile import SavedProfile
from src.daemon import apply_config


class FakeCPU:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def set_max_freq_all(self, freq: int) -> tuple[bool, str]:
        self.calls.append(freq)
        return True, "cpu"


class FakePower:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def set_preset(self, preset: str) -> tuple[bool, str]:
        self.calls.append(preset)
        return True, "power"


class FakeFans:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def set_profile(self, profile: str) -> tuple[bool, str]:
        self.calls.append(("set_profile", profile))
        return True, "profile"

    def set_fan_curve_preset(self, preset: str, profile: str) -> tuple[bool, str]:
        self.calls.append(("set_fan_curve_preset", preset, profile))
        return True, "curve"

    def enable_custom_curves(self, profile: str, enable: bool = True) -> tuple[bool, str]:
        self.calls.append(("enable_custom_curves", profile, enable))
        return True, "custom"

    def reset_fan_curve(self, profile: str) -> tuple[bool, str]:
        self.calls.append(("reset_fan_curve", profile))
        return True, "reset"


def test_daemon_applies_saved_profile() -> None:
    cpu = FakeCPU()
    power = FakePower()
    fans = FakeFans()
    profile = SavedProfile(
        cpu_freq=2_500_000,
        power_preset="silent",
        fan_profile="Balanced",
        fan_curve="aggressive",
    )

    assert apply_config(cpu, power, fans, profile)
    assert cpu.calls == [2_500_000]
    assert power.calls == ["silent"]
    assert fans.calls == [
        ("set_profile", "Balanced"),
        ("set_fan_curve_preset", "aggressive", "Balanced"),
        ("enable_custom_curves", "Balanced", True),
    ]


def test_daemon_applies_fan_reset() -> None:
    fans = FakeFans()
    profile = SavedProfile(fan_profile="Quiet", fan_reset=True)

    assert apply_config(FakeCPU(), FakePower(), fans, profile)
    assert fans.calls == [
        ("set_profile", "Quiet"),
        ("reset_fan_curve", "Quiet"),
        ("enable_custom_curves", "Quiet", False),
    ]
