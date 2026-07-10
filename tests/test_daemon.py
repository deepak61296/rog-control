from __future__ import annotations

from src.core.profile import SavedProfile
from src.daemon import ThermalWatchdog, apply_config, profile_file_is_safe


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


def test_watchdog_trips_only_after_sustained_overtemp() -> None:
    watchdog = ThermalWatchdog(trip_temp_c=93.0, hold_seconds=20.0, clear_temp_c=80.0)

    assert not watchdog.check(96.0, now=0.0)
    assert not watchdog.check(96.0, now=10.0)
    assert watchdog.check(96.0, now=20.0)
    assert watchdog.tripped
    # Latched: fires once, not repeatedly.
    assert not watchdog.check(96.0, now=22.0)


def test_watchdog_ignores_brief_spikes_and_missing_readings() -> None:
    watchdog = ThermalWatchdog(trip_temp_c=93.0, hold_seconds=20.0, clear_temp_c=80.0)

    assert not watchdog.check(96.0, now=0.0)
    assert not watchdog.check(85.0, now=10.0)  # dipped below trip: timer resets
    assert not watchdog.check(96.0, now=12.0)
    assert not watchdog.check(None, now=20.0)  # sensor gap: timer resets
    assert not watchdog.check(96.0, now=31.0)
    assert not watchdog.tripped


def test_watchdog_rearms_after_cooldown() -> None:
    watchdog = ThermalWatchdog(trip_temp_c=93.0, hold_seconds=20.0, clear_temp_c=80.0)

    watchdog.check(96.0, now=0.0)
    assert watchdog.check(96.0, now=20.0)
    assert not watchdog.check(90.0, now=30.0)  # still hot: stays latched
    assert watchdog.tripped
    assert not watchdog.check(75.0, now=40.0)  # cooled below clear: re-armed
    assert not watchdog.tripped
    watchdog.check(96.0, now=50.0)
    assert watchdog.check(96.0, now=70.0)


def test_profile_file_safety_rejects_non_root_and_writable(tmp_path) -> None:
    path = tmp_path / "profile.json"
    path.write_text("{}", encoding="utf-8")

    # Not owned by root (tests do not run as root).
    safe, reason = profile_file_is_safe(str(path))
    assert not safe
    assert "not owned by root" in reason

    safe, reason = profile_file_is_safe(str(tmp_path / "missing.json"))
    assert not safe
