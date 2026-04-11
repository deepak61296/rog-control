"""CPU frequency control module"""
import os
import glob
import subprocess
from typing import List, Optional


class CPUController:
    """Controls CPU frequency scaling"""

    CPU_PATH = "/sys/devices/system/cpu"

    # Preset frequencies in kHz
    FREQ_PRESETS = {
        'ultra_low': 1500000,   # 1.5 GHz
        'low': 2000000,         # 2.0 GHz
        'eco': 2500000,         # 2.5 GHz
        'cool': 3000000,        # 3.0 GHz
        'balanced': 3500000,    # 3.5 GHz
        'performance': 4000000, # 4.0 GHz
        'high': 4500000,        # 4.5 GHz
        'max': 5263000,         # 5.26 GHz (hardware max)
    }

    def __init__(self):
        self.num_cores = self._count_cores()
        self.hw_max_freq = self._get_hw_max_freq()
        self.hw_min_freq = self._get_hw_min_freq()

    def _count_cores(self) -> int:
        """Count number of CPU cores"""
        return len(glob.glob(f"{self.CPU_PATH}/cpu[0-9]*"))

    def _get_hw_max_freq(self) -> int:
        """Get hardware maximum frequency"""
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/cpuinfo_max_freq", 'r') as f:
                return int(f.read().strip())
        except:
            return 5263000  # Default for G14 2023

    def _get_hw_min_freq(self) -> int:
        """Get hardware minimum frequency"""
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/cpuinfo_min_freq", 'r') as f:
                return int(f.read().strip())
        except:
            return 400000  # 400 MHz

    def get_current_freq(self, core: int = 0) -> int:
        """Get current frequency for a core in kHz"""
        try:
            with open(f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_cur_freq", 'r') as f:
                return int(f.read().strip())
        except:
            return 0

    def get_max_freq(self, core: int = 0) -> int:
        """Get current max frequency limit for a core in kHz"""
        try:
            with open(f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_max_freq", 'r') as f:
                return int(f.read().strip())
        except:
            return self.hw_max_freq

    def get_all_core_freqs(self) -> List[int]:
        """Get current frequency for all cores"""
        return [self.get_current_freq(i) for i in range(self.num_cores)]

    def get_governor(self) -> str:
        """Get current CPU governor"""
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/scaling_governor", 'r') as f:
                return f.read().strip()
        except:
            return "unknown"

    def get_available_governors(self) -> List[str]:
        """Get list of available governors"""
        try:
            with open(f"{self.CPU_PATH}/cpu0/cpufreq/scaling_available_governors", 'r') as f:
                return f.read().strip().split()
        except:
            return []

    def set_max_freq(self, freq_khz: int, cores: Optional[List[int]] = None) -> bool:
        """Set maximum frequency for specified cores (or all cores)"""
        # Clamp to valid range
        freq_khz = max(self.hw_min_freq, min(freq_khz, self.hw_max_freq))

        if cores is None:
            cores = list(range(self.num_cores))

        success = True
        for core in cores:
            path = f"{self.CPU_PATH}/cpu{core}/cpufreq/scaling_max_freq"
            try:
                # Try direct write first
                with open(path, 'w') as f:
                    f.write(str(freq_khz))
            except PermissionError:
                # Fall back to sudo
                result = subprocess.run(
                    ['sudo', 'tee', path],
                    input=str(freq_khz).encode(),
                    capture_output=True
                )
                if result.returncode != 0:
                    success = False

        return success

    def set_max_freq_all(self, freq_khz: int) -> bool:
        """Set maximum frequency for all cores using shell"""
        cmd = f'for i in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do echo {freq_khz} | sudo tee "$i" > /dev/null; done'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0

    def set_governor(self, governor: str) -> bool:
        """Set CPU governor for all cores"""
        if governor not in self.get_available_governors():
            return False

        cmd = f'for i in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo {governor} | sudo tee "$i" > /dev/null; done'
        result = subprocess.run(cmd, shell=True, capture_output=True)
        return result.returncode == 0

    def set_preset(self, preset_name: str) -> bool:
        """Set frequency from a named preset"""
        if preset_name in self.FREQ_PRESETS:
            return self.set_max_freq_all(self.FREQ_PRESETS[preset_name])
        return False

    @staticmethod
    def freq_to_ghz(freq_khz: int) -> float:
        """Convert kHz to GHz"""
        return freq_khz / 1000000.0

    @staticmethod
    def ghz_to_freq(ghz: float) -> int:
        """Convert GHz to kHz"""
        return int(ghz * 1000000)
