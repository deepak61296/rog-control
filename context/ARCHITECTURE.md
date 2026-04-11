# ROG Control - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ROG Control TUI                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Rich UI Layer                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │   │
│  │  │ Dashboard│ │ CPU Ctrl │ │Power Ctrl│ │Fan Ctrl│  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Core Layer                        │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │   │
│  │  │ cpu.py │ │power.py│ │ fans.py│ │sensors │        │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘        │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
└────────────────────────────│────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌──────────┐         ┌─────────┐
   │  sysfs  │         │ ryzenadj │         │ asusctl │
   │ (kernel)│         │  (CLI)   │         │  (CLI)  │
   └─────────┘         └──────────┘         └─────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────────────────────────────────────────────┐
   │                   Hardware                       │
   │  CPU (AMD Ryzen)  │  iGPU  │  Fans  │  Sensors  │
   └─────────────────────────────────────────────────┘
```

## Module Responsibilities

### UI Layer (`src/ui/`)

**app.py** - Main application
- Initialize Rich console and layout
- Handle keyboard input
- Manage screen updates (async)
- Route to different views

**widgets.py** - Custom components
- GaugeWidget - Animated progress bars
- StatsPanel - Live updating stats
- MenuWidget - Navigation menus
- GraphWidget - Mini sparkline graphs

**themes.py** - Visual theming
- Color schemes
- Unicode characters for UI elements
- Animation timings

### Core Layer (`src/core/`)

**cpu.py** - CPU frequency control
```python
class CPUController:
    def get_current_freq(core: int) -> int
    def get_max_freq(core: int) -> int
    def set_max_freq(freq_khz: int, cores: list[int] = None)
    def get_governor() -> str
    def set_governor(gov: str)
    def get_all_cores_freq() -> list[int]
```

**power.py** - RyzenAdj wrapper
```python
class PowerController:
    def get_power_info() -> dict
    def set_stapm_limit(mw: int)
    def set_fast_limit(mw: int)
    def set_slow_limit(mw: int)
    def set_tctl_temp(celsius: int)
    def set_vrm_current(ma: int)
    def set_preset(name: str)
    def apply_settings(settings: dict)
```

**fans.py** - Fan control via asusctl
```python
class FanController:
    def get_fan_speeds() -> tuple[int, int]
    def get_profile() -> str
    def set_profile(profile: str)
    def set_fan_curve(fan: str, curve: list[tuple[int, int]])
    def enable_custom_curve(enable: bool)
```

**sensors.py** - Temperature/power readings
```python
class SensorReader:
    def get_cpu_temp() -> float
    def get_gpu_temp() -> float
    def get_gpu_power() -> float
    def get_nvme_temp() -> float
    def get_battery_info() -> dict
    def detect_hwmon_paths() -> dict  # Auto-detect paths
```

**gpu.py** - GPU control
```python
class GPUController:
    def get_igpu_clock() -> int
    def get_igpu_power() -> float
    def set_igpu_max_clock(mhz: int)
    def get_dgpu_info() -> dict  # NVIDIA via nvidia-smi
```

### Utils Layer (`src/utils/`)

**config.py** - Configuration management
```python
class Config:
    def load() -> dict
    def save(config: dict)
    def get_preset(name: str) -> dict
    def save_preset(name: str, settings: dict)
```

**helpers.py** - Utility functions
```python
def read_sysfs(path: str) -> str
def write_sysfs(path: str, value: str) -> bool
def run_command(cmd: list[str], sudo: bool = False) -> str
def format_freq(khz: int) -> str  # "3.0 GHz"
def format_power(mw: int) -> str  # "45 W"
def format_temp(celsius: float) -> str  # "65.2°C"
```

## Data Flow

### Reading Sensors (every 1-2 seconds)
```
SensorReader.get_cpu_temp()
    → read /sys/class/hwmon/hwmon5/temp1_input
    → parse and convert (millidegrees → degrees)
    → return float

Dashboard.update()
    → call all SensorReader methods
    → update Rich Live display
```

### Setting Power Limit
```
User presses key → MenuWidget
    → PowerController.set_stapm_limit(45000)
    → subprocess.run(['sudo', 'ryzenadj', '--stapm-limit=45000'])
    → verify with get_power_info()
    → update UI
```

## Threading Model
```
Main Thread:
    - Rich Live display updates
    - Keyboard input handling

Background Thread (daemon):
    - Sensor polling every 1 second
    - Updates shared state dict
    - Main thread reads state for display
```

## Error Handling Strategy
1. Never crash on sysfs read failures (return None/default)
2. Show user-friendly error messages in UI
3. Log errors to ~/.cache/rog-control/error.log
4. Graceful degradation (if ryzenadj fails, disable power controls)
