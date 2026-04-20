"""Sensor reading module for temperature, power, and fan monitoring"""
import os
import subprocess
import glob
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SystemStats:
    """Container for all system statistics"""
    cpu_temp: float = 0.0
    gpu_temp: float = 0.0
    nvme_temp: float = 0.0
    cpu_fan_rpm: int = 0
    gpu_fan_rpm: int = 0
    cpu_freq_current: int = 0
    cpu_freq_max: int = 0
    gpu_clock: int = 0
    gpu_power: float = 0.0
    cpu_power: float = 0.0
    battery_percent: int = 0
    battery_power: float = 0.0
    battery_status: str = ""
    # NVIDIA GPU stats (if available)
    has_nvidia: bool = False
    nvidia_temp: float = 0.0
    nvidia_power: float = 0.0
    nvidia_clock: int = 0
    nvidia_util: int = 0
    nvidia_vram_used: int = 0
    nvidia_vram_total: int = 0


class SensorReader:
    """Reads system sensors from sysfs and other sources"""

    def __init__(self):
        self._hwmon_paths = self._detect_hwmon_paths()
        self._has_nvidia = self._check_nvidia()

    def _check_nvidia(self) -> bool:
        """Check if NVIDIA GPU is available"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() != ""
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_nvidia_stats(self) -> Dict:
        """Get NVIDIA GPU stats using nvidia-smi"""
        if not self._has_nvidia:
            return {
                'temp': 0.0, 'power': 0.0, 'clock': 0, 'util': 0,
                'vram_used': 0, 'vram_total': 0
            }
        
        try:
            # Query multiple GPU metrics at once for efficiency
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=temperature.gpu,power.draw,clocks.gr,utilization.gpu,memory.used,memory.total',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                if len(parts) >= 6:
                    return {
                        'temp': float(parts[0].strip()),
                        'power': float(parts[1].strip()),
                        'clock': int(parts[2].strip()),
                        'util': int(parts[3].strip()),
                        'vram_used': int(parts[4].strip()),
                        'vram_total': int(parts[5].strip())
                    }
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            pass
        
        return {
            'temp': 0.0, 'power': 0.0, 'clock': 0, 'util': 0,
            'vram_used': 0, 'vram_total': 0
        }

    def _detect_hwmon_paths(self) -> Dict[str, str]:
        """Auto-detect hwmon paths by reading name files"""
        paths = {}
        for hwmon_dir in glob.glob('/sys/class/hwmon/hwmon*'):
            name_file = os.path.join(hwmon_dir, 'name')
            if os.path.exists(name_file):
                try:
                    with open(name_file, 'r') as f:
                        name = f.read().strip()
                    paths[name] = hwmon_dir
                except:
                    pass
        return paths

    def _read_sysfs(self, path: str) -> Optional[str]:
        """Read a sysfs file safely"""
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except (IOError, PermissionError, FileNotFoundError):
            return None

    def _read_int(self, path: str, default: int = 0) -> int:
        """Read an integer from sysfs"""
        val = self._read_sysfs(path)
        if val is not None:
            try:
                return int(val)
            except ValueError:
                pass
        return default

    def _read_float(self, path: str, default: float = 0.0) -> float:
        """Read a float from sysfs"""
        val = self._read_sysfs(path)
        if val is not None:
            try:
                return float(val)
            except ValueError:
                pass
        return default

    def get_cpu_temp(self) -> float:
        """Get CPU temperature in Celsius"""
        # k10temp for AMD
        if 'k10temp' in self._hwmon_paths:
            path = os.path.join(self._hwmon_paths['k10temp'], 'temp1_input')
            return self._read_int(path) / 1000.0
        return 0.0

    def get_gpu_temp(self) -> float:
        """Get GPU temperature in Celsius"""
        if 'amdgpu' in self._hwmon_paths:
            path = os.path.join(self._hwmon_paths['amdgpu'], 'temp1_input')
            return self._read_int(path) / 1000.0
        return 0.0

    def get_nvme_temp(self) -> float:
        """Get NVMe SSD temperature"""
        if 'nvme' in self._hwmon_paths:
            path = os.path.join(self._hwmon_paths['nvme'], 'temp1_input')
            return self._read_int(path) / 1000.0
        return 0.0

    def get_fan_speeds(self) -> Tuple[int, int]:
        """Get CPU and GPU fan speeds in RPM"""
        if 'asus' in self._hwmon_paths:
            base = self._hwmon_paths['asus']
            cpu_fan = self._read_int(os.path.join(base, 'fan1_input'))
            gpu_fan = self._read_int(os.path.join(base, 'fan2_input'))
            return cpu_fan, gpu_fan
        # Fallback to hardcoded path
        cpu_fan = self._read_int('/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan1_input')
        gpu_fan = self._read_int('/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan2_input')
        return cpu_fan, gpu_fan

    def get_cpu_freq(self) -> Tuple[int, int]:
        """Get current and max CPU frequency in MHz"""
        cur = self._read_int('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq')
        max_freq = self._read_int('/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq')
        return cur // 1000, max_freq // 1000  # Convert to MHz

    def get_gpu_clock(self) -> int:
        """Get GPU clock speed in MHz"""
        if 'amdgpu' in self._hwmon_paths:
            path = os.path.join(self._hwmon_paths['amdgpu'], 'freq1_input')
            return self._read_int(path) // 1000000  # Hz to MHz
        return 0

    def get_gpu_power(self) -> float:
        """Get GPU power consumption in Watts"""
        if 'amdgpu' in self._hwmon_paths:
            path = os.path.join(self._hwmon_paths['amdgpu'], 'power1_average')
            return self._read_int(path) / 1000000.0  # microwatts to watts
        return 0.0

    def get_cpu_power(self) -> float:
        """Get CPU power from ryzenadj (cached, expensive call)"""
        # This is expensive, should be called less frequently
        return 0.0  # Placeholder - will be updated by PowerController

    def get_battery_info(self) -> Dict:
        """Get battery information"""
        base = '/sys/class/power_supply/BAT0'
        return {
            'percent': self._read_int(os.path.join(base, 'capacity')),
            'status': self._read_sysfs(os.path.join(base, 'status')) or 'Unknown',
            'power': self._read_int(os.path.join(base, 'power_now')) / 1000000.0,  # W
        }

    def get_all_stats(self) -> SystemStats:
        """Get all system statistics at once"""
        cpu_fan, gpu_fan = self.get_fan_speeds()
        cpu_cur, cpu_max = self.get_cpu_freq()
        battery = self.get_battery_info()
        nvidia = self.get_nvidia_stats()

        return SystemStats(
            cpu_temp=self.get_cpu_temp(),
            gpu_temp=self.get_gpu_temp(),
            nvme_temp=self.get_nvme_temp(),
            cpu_fan_rpm=cpu_fan,
            gpu_fan_rpm=gpu_fan,
            cpu_freq_current=cpu_cur,
            cpu_freq_max=cpu_max,
            gpu_clock=self.get_gpu_clock(),
            gpu_power=self.get_gpu_power(),
            battery_percent=battery['percent'],
            battery_power=battery['power'],
            battery_status=battery['status'],
            # NVIDIA GPU stats
            has_nvidia=self._has_nvidia,
            nvidia_temp=nvidia['temp'],
            nvidia_power=nvidia['power'],
            nvidia_clock=nvidia['clock'],
            nvidia_util=nvidia['util'],
            nvidia_vram_used=nvidia['vram_used'],
            nvidia_vram_total=nvidia['vram_total'],
        )
