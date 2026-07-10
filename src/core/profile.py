"""Persistent profile storage for ROG Control."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.process import run_command


PROFILE_DIR = "/etc/rog-control"
PROFILE_PATH = f"{PROFILE_DIR}/profile.json"
PROFILE_TMP_PATH = f"{PROFILE_PATH}.tmp"

CPU_FREQ_MIN = 400_000
CPU_FREQ_MAX = 4_500_000
POWER_PRESETS = {"silent", "battery", "pd", "ac", "eco", "cool", "balanced", "performance", "high"}
FAN_PROFILES = {"Performance", "Balanced", "Quiet"}
FAN_CURVES = {"aggressive", "max"}


@dataclass(frozen=True)
class SavedProfile:
    """Validated persisted settings."""

    cpu_freq: int | None = None
    power_preset: str | None = None
    fan_profile: str | None = None
    fan_curve: str | None = None
    fan_reset: bool = False
    unknown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.unknown)
        if self.cpu_freq is not None:
            data["cpu_freq"] = self.cpu_freq
        if self.power_preset is not None:
            data["power_preset"] = self.power_preset
        if self.fan_profile is not None:
            data["fan_profile"] = self.fan_profile
        if self.fan_curve is not None:
            data["fan_curve"] = self.fan_curve
        if self.fan_reset:
            data["fan_reset"] = True
        return data

    def merged(self, updates: dict[str, Any]) -> "SavedProfile":
        data = self.to_dict()
        if "fan_curve" in updates:
            data.pop("fan_reset", None)
        if "fan_reset" in updates:
            data.pop("fan_curve", None)
        data.update(updates)
        return validate_profile(data)


class ProfileStore:
    """Read and write the persistent profile file."""

    def __init__(self, path: str = PROFILE_PATH, use_sudo: bool | None = None) -> None:
        self.path = path
        self.tmp_path = f"{path}.tmp"
        self.directory = str(Path(path).parent)
        self.use_sudo = (os.geteuid() != 0) if use_sudo is None else use_sudo

    def load(self) -> tuple[SavedProfile, str | None]:
        success, output = self._read_text()
        if not success:
            return SavedProfile(), output
        if not output.strip():
            return SavedProfile(), None
        try:
            raw = json.loads(output)
        except json.JSONDecodeError as exc:
            return SavedProfile(), f"Invalid profile JSON: {exc}"
        try:
            return validate_profile(raw), None
        except ValueError as exc:
            return SavedProfile(), str(exc)

    def save_updates(self, updates: dict[str, Any]) -> tuple[bool, str]:
        profile, error = self.load()
        if error and "not found" not in error.lower() and "no such file" not in error.lower():
            return False, error
        try:
            merged = profile.merged(updates)
        except ValueError as exc:
            return False, str(exc)
        return self.save(merged)

    def save(self, profile: SavedProfile) -> tuple[bool, str]:
        content = json.dumps(profile.to_dict(), indent=2, sort_keys=True) + "\n"
        commands = [
            (["install", "-d", "-m", "0755", self.directory], None),
            (["tee", self.tmp_path], content),
            (["chmod", "0644", self.tmp_path], None),
            (["mv", self.tmp_path, self.path], None),
        ]
        for cmd, input_data in commands:
            success, output = self._run(cmd, input_data=input_data)
            if not success:
                return False, output
        return True, "Profile saved"

    def _read_text(self) -> tuple[bool, str]:
        if not self.use_sudo:
            try:
                return True, Path(self.path).read_text(encoding="utf-8")
            except FileNotFoundError:
                return True, ""
            except OSError as exc:
                return False, str(exc)
        success, output = self._run(["cat", self.path])
        if not success and ("No such file" in output or "not found" in output):
            return True, ""
        return success, output

    def _run(self, cmd: list[str], input_data: str | None = None) -> tuple[bool, str]:
        if self.use_sudo:
            cmd = ["sudo", "-n", *cmd]
        return run_command(cmd, input_data=input_data, start_new_session=False)


def validate_profile(raw: Any) -> SavedProfile:
    if not isinstance(raw, dict):
        raise ValueError("Profile must be a JSON object")

    known = {"cpu_freq", "power_preset", "fan_profile", "fan_curve", "fan_reset"}
    unknown = {key: value for key, value in raw.items() if key not in known}

    cpu_freq = raw.get("cpu_freq")
    if cpu_freq is not None:
        if not isinstance(cpu_freq, int) or isinstance(cpu_freq, bool):
            raise ValueError("cpu_freq must be an integer kHz value")
        if not CPU_FREQ_MIN <= cpu_freq <= CPU_FREQ_MAX:
            raise ValueError(f"cpu_freq must be between {CPU_FREQ_MIN} and {CPU_FREQ_MAX}")

    power_preset = raw.get("power_preset")
    if power_preset is not None and power_preset not in POWER_PRESETS:
        raise ValueError(f"Unsupported power preset: {power_preset}")

    fan_profile = raw.get("fan_profile")
    if fan_profile is not None and fan_profile not in FAN_PROFILES:
        raise ValueError(f"Unsupported fan profile: {fan_profile}")

    fan_curve = raw.get("fan_curve")
    if fan_curve is not None and fan_curve not in FAN_CURVES:
        raise ValueError(f"Unsupported fan curve: {fan_curve}")

    fan_reset = bool(raw.get("fan_reset", False))
    if fan_curve is not None and fan_reset:
        raise ValueError("fan_curve and fan_reset are mutually exclusive")

    return SavedProfile(
        cpu_freq=cpu_freq,
        power_preset=power_preset,
        fan_profile=fan_profile,
        fan_curve=fan_curve,
        fan_reset=fan_reset,
        unknown=unknown,
    )
