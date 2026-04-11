"""RyzenAdj power management module"""
import subprocess
import re
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PowerInfo:
    """Container for power metrics"""
    stapm_limit: float = 0.0
    stapm_value: float = 0.0
    fast_limit: float = 0.0
    fast_value: float = 0.0
    slow_limit: float = 0.0
    slow_value: float = 0.0
    tctl_limit: float = 95.0
    tctl_value: float = 0.0
    vrm_current: float = 0.0
    vrm_current_limit: float = 0.0
    vrm_max_current: float = 0.0
    vrm_max_current_limit: float = 0.0
    apu_power: float = 0.0


class PowerController:
    """Controls AMD Ryzen power management via ryzenadj"""

    # Power presets (all values in mW)
    POWER_PRESETS = {
        'silent': {
            'stapm': 15000,
            'fast': 20000,
            'slow': 15000,
            'tctl': 75,
            'description': 'Silent - 15W, very quiet'
        },
        'eco': {
            'stapm': 25000,
            'fast': 35000,
            'slow': 25000,
            'tctl': 80,
            'description': 'Eco - 25W, battery friendly'
        },
        'cool': {
            'stapm': 35000,
            'fast': 45000,
            'slow': 35000,
            'tctl': 85,
            'description': 'Cool - 35W, good thermals'
        },
        'balanced': {
            'stapm': 45000,
            'fast': 55000,
            'slow': 45000,
            'tctl': 90,
            'description': 'Balanced - 45W, recommended'
        },
        'performance': {
            'stapm': 55000,
            'fast': 65000,
            'slow': 55000,
            'tctl': 95,
            'description': 'Performance - 55W'
        },
        'high': {
            'stapm': 65000,
            'fast': 75000,
            'slow': 65000,
            'tctl': 95,
            'description': 'High - 65W, hot'
        },
        'max': {
            'stapm': 80000,
            'fast': 80000,
            'slow': 80000,
            'tctl': 100,
            'description': 'Max - 80W, very hot!'
        },
    }

    def __init__(self):
        self.ryzenadj_path = self._find_ryzenadj()
        self._last_info: Optional[PowerInfo] = None

    def _find_ryzenadj(self) -> str:
        """Find ryzenadj binary"""
        result = subprocess.run(['which', 'ryzenadj'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        # Check common locations
        for path in ['/usr/local/bin/ryzenadj', '/usr/bin/ryzenadj']:
            import os
            if os.path.exists(path):
                return path
        return 'ryzenadj'

    def _run_ryzenadj(self, args: list) -> tuple[bool, str]:
        """Run ryzenadj with sudo"""
        cmd = ['sudo', self.ryzenadj_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout + result.stderr

    def get_power_info(self) -> PowerInfo:
        """Get current power metrics from ryzenadj"""
        success, output = self._run_ryzenadj(['-i'])

        info = PowerInfo()
        if not success:
            return info

        # Parse the table output - format is:
        # | STAPM LIMIT         |    45.000 | stapm-limit        |
        for line in output.split('\n'):
            if '|' not in line:
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 3:
                continue

            name = parts[1].strip() if len(parts) > 1 else ""
            value_str = parts[2].strip() if len(parts) > 2 else ""

            try:
                value = float(value_str)
            except (ValueError, TypeError):
                continue

            # Map names to attributes
            if 'STAPM LIMIT' in name:
                info.stapm_limit = value
            elif 'STAPM VALUE' in name:
                info.stapm_value = value
            elif 'PPT LIMIT FAST' in name:
                info.fast_limit = value
            elif 'PPT VALUE FAST' in name:
                info.fast_value = value
            elif 'PPT LIMIT SLOW' in name:
                info.slow_limit = value
            elif 'PPT VALUE SLOW' in name:
                info.slow_value = value
            elif 'THM LIMIT CORE' in name:
                info.tctl_limit = value
            elif 'THM VALUE CORE' in name:
                info.tctl_value = value
            elif 'TDC LIMIT VDD' in name:
                info.vrm_current_limit = value
            elif 'TDC VALUE VDD' in name:
                info.vrm_current = value
            elif 'EDC LIMIT VDD' in name:
                info.vrm_max_current_limit = value
            elif 'EDC VALUE VDD' in name:
                info.vrm_max_current = value

        self._last_info = info
        return info

    def set_stapm_limit(self, mw: int) -> bool:
        """Set STAPM power limit in milliwatts"""
        success, _ = self._run_ryzenadj([f'--stapm-limit={mw}'])
        return success

    def set_fast_limit(self, mw: int) -> bool:
        """Set fast (PPT) power limit in milliwatts"""
        success, _ = self._run_ryzenadj([f'--fast-limit={mw}'])
        return success

    def set_slow_limit(self, mw: int) -> bool:
        """Set slow power limit in milliwatts"""
        success, _ = self._run_ryzenadj([f'--slow-limit={mw}'])
        return success

    def set_tctl_temp(self, celsius: int) -> bool:
        """Set temperature limit in Celsius"""
        success, _ = self._run_ryzenadj([f'--tctl-temp={celsius}'])
        return success

    def set_vrm_current(self, ma: int) -> bool:
        """Set VRM current limit (TDC) in milliamps"""
        success, _ = self._run_ryzenadj([f'--vrm-current={ma}'])
        return success

    def set_vrm_max_current(self, ma: int) -> bool:
        """Set VRM max current limit (EDC) in milliamps"""
        success, _ = self._run_ryzenadj([f'--vrmmax-current={ma}'])
        return success

    def set_gfx_clock(self, max_mhz: int, min_mhz: int = 400) -> bool:
        """Set iGPU clock limits"""
        success1, _ = self._run_ryzenadj([f'--max-gfxclk={max_mhz}'])
        success2, _ = self._run_ryzenadj([f'--min-gfxclk={min_mhz}'])
        return success1 and success2

    def set_power_saving(self) -> bool:
        """Enable power saving mode"""
        success, _ = self._run_ryzenadj(['--power-saving'])
        return success

    def set_max_performance(self) -> bool:
        """Enable max performance mode"""
        success, _ = self._run_ryzenadj(['--max-performance'])
        return success

    def set_preset(self, preset_name: str) -> bool:
        """Apply a power preset"""
        if preset_name not in self.POWER_PRESETS:
            return False

        preset = self.POWER_PRESETS[preset_name]
        args = [
            f'--stapm-limit={preset["stapm"]}',
            f'--fast-limit={preset["fast"]}',
            f'--slow-limit={preset["slow"]}',
            f'--tctl-temp={preset["tctl"]}',
        ]
        success, _ = self._run_ryzenadj(args)
        return success

    def apply_custom(self, stapm: int, fast: int, slow: int, tctl: int = 95) -> bool:
        """Apply custom power settings"""
        args = [
            f'--stapm-limit={stapm}',
            f'--fast-limit={fast}',
            f'--slow-limit={slow}',
            f'--tctl-temp={tctl}',
        ]
        success, _ = self._run_ryzenadj(args)
        return success

    def get_current_power(self) -> float:
        """Get current CPU power draw in watts"""
        if self._last_info:
            return self._last_info.stapm_value
        info = self.get_power_info()
        return info.stapm_value
