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

logger = logging.getLogger(__name__)

CONFIG_PATH = ProfileStore().path


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
    store = ProfileStore(use_sudo=False)

    last_mtime = -1.0

    while True:
        try:
            if os.path.exists(store.path):
                mtime = os.path.getmtime(store.path)
                if mtime > last_mtime:
                    profile, error = store.load()
                    if error:
                        logger.error("Failed to load profile: %s", error)
                    else:
                        logger.info("Profile changed, applying saved settings.")
                        apply_config(cpu, power, fans, profile)
                    last_mtime = mtime
        except Exception as exc:
            logger.error("Daemon error: %s", exc)

        time.sleep(10.0)

if __name__ == "__main__":
    sys.exit(main())
