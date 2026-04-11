"""Fan control module via asusctl"""
import subprocess
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class FanCurve:
    """Fan curve definition"""
    points: List[Tuple[int, int]]  # List of (temp, percent) points

    def to_asusctl_format(self) -> str:
        """Convert to asusctl format: 30c:50%,40c:60%,..."""
        return ','.join(f'{t}c:{p}%' for t, p in self.points)


class FanController:
    """Controls fans via asusctl"""

    # Predefined fan curves
    FAN_CURVES = {
        'silent': FanCurve([
            (30, 20), (40, 25), (50, 30), (60, 40),
            (70, 50), (80, 65), (90, 80), (100, 80)
        ]),
        'quiet': FanCurve([
            (30, 30), (40, 35), (50, 40), (60, 50),
            (70, 60), (80, 75), (90, 90), (100, 100)
        ]),
        'balanced': FanCurve([
            (30, 30), (40, 40), (50, 50), (60, 60),
            (70, 75), (80, 90), (90, 100), (100, 100)
        ]),
        'aggressive': FanCurve([
            (30, 50), (40, 55), (50, 60), (60, 70),
            (70, 80), (80, 90), (90, 100), (100, 100)
        ]),
        'max': FanCurve([
            (30, 100), (40, 100), (50, 100), (60, 100),
            (70, 100), (80, 100), (90, 100), (100, 100)
        ]),
    }

    PROFILES = ['Performance', 'Balanced', 'Quiet']

    def __init__(self):
        pass

    def _run_asusctl(self, args: list) -> tuple[bool, str]:
        """Run asusctl command"""
        cmd = ['asusctl'] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr

    def get_profile(self) -> str:
        """Get current power profile"""
        success, output = self._run_asusctl(['profile', '-p'])
        if success:
            for line in output.split('\n'):
                if 'Active profile' in line:
                    for profile in self.PROFILES:
                        if profile in line:
                            return profile
        return 'Unknown'

    def get_profile_settings(self) -> dict:
        """Get profile settings for AC and battery"""
        success, output = self._run_asusctl(['profile', '-p'])
        settings = {'active': 'Unknown', 'ac': 'Unknown', 'battery': 'Unknown'}

        if success:
            for line in output.split('\n'):
                if 'Active profile' in line:
                    for p in self.PROFILES:
                        if p in line:
                            settings['active'] = p
                elif 'AC' in line:
                    for p in self.PROFILES:
                        if p in line:
                            settings['ac'] = p
                elif 'Battery' in line:
                    for p in self.PROFILES:
                        if p in line:
                            settings['battery'] = p
        return settings

    def set_profile(self, profile: str) -> bool:
        """Set power profile"""
        if profile not in self.PROFILES:
            return False
        success, _ = self._run_asusctl(['profile', '-P', profile])
        return success

    def set_profile_ac(self, profile: str) -> bool:
        """Set profile for AC power"""
        if profile not in self.PROFILES:
            return False
        success, _ = self._run_asusctl(['profile', '-a', profile])
        return success

    def set_profile_battery(self, profile: str) -> bool:
        """Set profile for battery power"""
        if profile not in self.PROFILES:
            return False
        success, _ = self._run_asusctl(['profile', '-b', profile])
        return success

    def get_fan_curve_enabled(self) -> bool:
        """Check if custom fan curves are enabled"""
        success, output = self._run_asusctl(['fan-curve', '-g'])
        return 'enabled: true' in output.lower() if success else False

    def set_fan_curve(self, curve: FanCurve, fan: str = 'cpu', profile: str = 'Performance') -> bool:
        """Set fan curve for specified fan"""
        curve_str = curve.to_asusctl_format()
        success, _ = self._run_asusctl([
            'fan-curve', '-m', profile, '-f', fan, '-D', curve_str
        ])
        return success

    def set_fan_curve_preset(self, preset: str, profile: str = 'Performance') -> bool:
        """Set a predefined fan curve preset"""
        if preset not in self.FAN_CURVES:
            return False

        curve = self.FAN_CURVES[preset]
        success_cpu = self.set_fan_curve(curve, 'cpu', profile)
        success_gpu = self.set_fan_curve(curve, 'gpu', profile)
        return success_cpu and success_gpu

    def enable_custom_curves(self, profile: str = 'Performance', enable: bool = True) -> bool:
        """Enable or disable custom fan curves"""
        success, _ = self._run_asusctl([
            'fan-curve', '-m', profile, '-e', str(enable).lower()
        ])
        return success

    def reset_fan_curve(self, profile: str = 'Performance') -> bool:
        """Reset fan curves to default"""
        success, _ = self._run_asusctl(['fan-curve', '-m', profile, '-d'])
        return success

    def set_max_fans(self, profile: str = 'Performance') -> bool:
        """Set fans to maximum speed"""
        success = self.set_fan_curve_preset('max', profile)
        if success:
            success = self.enable_custom_curves(profile, True)
        return success

    def get_charge_limit(self) -> int:
        """Get battery charge limit"""
        success, output = self._run_asusctl(['-c', 'show'])
        # Parse output for charge limit
        # Default to 100 if can't determine
        return 100

    def set_charge_limit(self, percent: int) -> bool:
        """Set battery charge limit (20-100)"""
        percent = max(20, min(100, percent))
        success, _ = self._run_asusctl(['-c', str(percent)])
        return success
