"""Background daemon for ROG Control."""

import logging
import os
import subprocess
import sys
import time

from src.core.cpu import CPUController
from src.core.fans import FanController
from src.core.profile import ProfileStore, SavedProfile
from src.core.power import PowerController
from src.core.sensors import SensorReader

logger = logging.getLogger(__name__)

CONFIG_PATH = ProfileStore().path

POLL_SECONDS = 2.0


class ThermalWatchdog:
    """Trip protection when the CPU stays above a trip temperature.

    Only ever acts in the safe direction (reducing power limits). Once
    tripped it stays latched until the temperature falls below the clear
    threshold or the saved profile changes (explicit user intent).
    """

    def __init__(self, trip_temp_c: float = 93.0, hold_seconds: float = 20.0, clear_temp_c: float = 80.0):
        self.trip_temp_c = trip_temp_c
        self.hold_seconds = hold_seconds
        self.clear_temp_c = clear_temp_c
        self.tripped = False
        self._over_since: float | None = None

    def reset(self) -> None:
        self.tripped = False
        self._over_since = None

    def check(self, temp_c: float | None, now: float) -> bool:
        """Return True exactly once, at the moment protection should fire."""
        if temp_c is None:
            self._over_since = None
            return False

        if self.tripped:
            if temp_c <= self.clear_temp_c:
                logger.warning("Thermal watchdog re-armed: CPU cooled to %.1f°C", temp_c)
                self.reset()
            return False

        if temp_c < self.trip_temp_c:
            self._over_since = None
            return False

        if self._over_since is None:
            self._over_since = now
        if now - self._over_since >= self.hold_seconds:
            self.tripped = True
            return True
        return False


def profile_file_is_safe(path: str) -> tuple[bool, str]:
    """The root daemon must only apply a profile root owns exclusively."""
    try:
        status = os.stat(path)
    except OSError as exc:
        return False, str(exc)
    if status.st_uid != 0:
        return False, f"{path} is not owned by root"
    if status.st_mode & 0o022:
        return False, f"{path} is group/world writable"
    return True, ""


def apply_config(cpu: CPUController, power: PowerController, fans: FanController, profile: SavedProfile) -> bool:
    success = True

    if profile.cpu_freq is not None:
        step_success, message = cpu.set_max_freq_all(profile.cpu_freq)
        success = success and step_success
        _log_step("CPU frequency", step_success, message)

    if profile.power_preset is not None:
        step_success, message = power.set_preset(profile.power_preset)
        success = success and step_success
        _log_step("Power preset", step_success, message)

    if profile.fan_profile is not None:
        step_success, message = fans.set_profile(profile.fan_profile)
        success = success and step_success
        _log_step("Fan profile", step_success, message)

    if profile.fan_curve is not None:
        target_profile = profile.fan_profile or "Performance"
        step_success, message = fans.set_fan_curve_preset(profile.fan_curve, target_profile)
        success = success and step_success
        _log_step("Fan curve", step_success, message)
        if step_success:
            step_success, message = fans.enable_custom_curves(target_profile, enable=True)
            success = success and step_success
            _log_step("Custom fan curves", step_success, message)
    elif profile.fan_reset:
        target_profile = profile.fan_profile or "Performance"
        step_success, message = fans.reset_fan_curve(target_profile)
        success = success and step_success
        _log_step("Fan curve reset", step_success, message)
        if step_success:
            step_success, message = fans.enable_custom_curves(target_profile, enable=False)
            success = success and step_success
            _log_step("Firmware fan control", step_success, message)

    return success


def _log_step(name: str, success: bool, message: str) -> None:
    if success:
        logger.info("%s applied: %s", name, message)
    else:
        logger.error("%s failed: %s", name, message)


def main() -> int:
    if os.geteuid() != 0:
        print("rog-daemon must be run as root.")
        return 1

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("Starting ROG Control Daemon")

    # Stop conflicting services that might override CPU/Power
    subprocess.run(["systemctl", "stop", "power-profiles-daemon"], check=False, stderr=subprocess.DEVNULL)
    subprocess.run(["systemctl", "stop", "tlp"], check=False, stderr=subprocess.DEVNULL)

    cpu = CPUController()
    power = PowerController()
    fans = FanController()
    sensors = SensorReader()
    store = ProfileStore(use_sudo=False)
    watchdog = ThermalWatchdog()

    last_mtime = -1.0

    while True:
        try:
            if os.path.exists(store.path):
                mtime = os.path.getmtime(store.path)
                if mtime > last_mtime:
                    safe, reason = profile_file_is_safe(store.path)
                    if not safe:
                        logger.error("Refusing profile: %s", reason)
                    else:
                        profile, error = store.load()
                        if error:
                            logger.error("Failed to load profile: %s", error)
                        else:
                            logger.info("Profile changed, applying saved settings.")
                            watchdog.reset()
                            apply_config(cpu, power, fans, profile)
                    last_mtime = mtime

            temp_c = sensors.read_cpu_temp()
            if watchdog.check(temp_c, time.monotonic()):
                logger.critical(
                    "Thermal watchdog tripped at %.1f°C: forcing 'cool' power preset", temp_c
                )
                success, message = power.set_preset("cool")
                _log_step("Watchdog power preset", success, message)
        except Exception as exc:
            logger.error("Daemon error: %s", exc)

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    sys.exit(main())
