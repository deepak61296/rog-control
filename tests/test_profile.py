from __future__ import annotations

import json

from src.core.power import PowerController
from src.core.profile import ProfileStore, SavedProfile, validate_profile


def test_validate_profile_rejects_unsafe_cpu_limit() -> None:
    try:
        validate_profile({"cpu_freq": 5_263_000})
    except ValueError as exc:
        assert "cpu_freq" in str(exc)
    else:
        raise AssertionError("unsafe CPU limit was accepted")


def test_validate_profile_rejects_conflicting_fan_settings() -> None:
    try:
        validate_profile({"fan_curve": "max", "fan_reset": True})
    except ValueError as exc:
        assert "mutually exclusive" in str(exc)
    else:
        raise AssertionError("conflicting fan settings were accepted")


def test_validate_profile_accepts_quick_only_power_presets() -> None:
    for preset in ("battery", "pd", "ac"):
        assert validate_profile({"power_preset": preset}).power_preset == preset


def test_quick_only_power_presets_remain_conservative() -> None:
    assert PowerController.POWER_PRESETS["battery"] == {"stapm": 25000, "fast": 30000, "slow": 25000, "tctl": 80}
    assert PowerController.POWER_PRESETS["pd"] == {"stapm": 20000, "fast": 25000, "slow": 20000, "tctl": 80}
    assert PowerController.POWER_PRESETS["ac"] == {"stapm": 30000, "fast": 35000, "slow": 30000, "tctl": 85}


def test_profile_store_saves_atomically_with_sudo(monkeypatch) -> None:
    calls = []

    def fake_run_command(cmd, input_data=None, start_new_session=True, **kwargs):
        calls.append((cmd, input_data, start_new_session))
        if cmd[-1] == "/etc/rog-control/profile.json":
            return True, ""
        return True, ""

    monkeypatch.setattr("src.core.profile.os.geteuid", lambda: 1000)
    monkeypatch.setattr("src.core.profile.run_command", fake_run_command)

    store = ProfileStore()
    success, message = store.save(SavedProfile(cpu_freq=2_500_000, power_preset="silent"))

    assert success, message
    assert calls[0] == (["sudo", "-n", "install", "-d", "-m", "0755", "/etc/rog-control"], None, False)
    assert calls[1][0] == ["sudo", "-n", "tee", "/etc/rog-control/profile.json.tmp"]
    assert json.loads(calls[1][1]) == {"cpu_freq": 2_500_000, "power_preset": "silent"}
    assert calls[2] == (["sudo", "-n", "chmod", "0644", "/etc/rog-control/profile.json.tmp"], None, False)
    assert calls[3] == (
        ["sudo", "-n", "mv", "/etc/rog-control/profile.json.tmp", "/etc/rog-control/profile.json"],
        None,
        False,
    )


def test_profile_store_merges_mutually_exclusive_fan_keys(monkeypatch) -> None:
    store = ProfileStore(use_sudo=False)
    monkeypatch.setattr(store, "_read_text", lambda: (True, '{"fan_reset": true, "fan_profile": "Balanced"}'))

    saved = []
    monkeypatch.setattr(store, "save", lambda profile: saved.append(profile) or (True, "Profile saved"))

    success, message = store.save_updates({"fan_curve": "aggressive", "fan_profile": "Performance"})

    assert success, message
    assert saved[0].to_dict() == {"fan_curve": "aggressive", "fan_profile": "Performance"}
