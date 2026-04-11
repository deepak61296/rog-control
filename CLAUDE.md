# ROG Control - AI Agent Context

## Project Overview
ROG Control is a terminal UI (TUI) application for controlling thermals, fans, and power management on ASUS ROG Zephyrus G14 (2023) laptops running Linux.

## Target Device
- **Model:** ASUS ROG Zephyrus G14 (2023)
- **CPU:** AMD Ryzen 7040 series (Phoenix Point)
- **GPU:** AMD Radeon integrated + NVIDIA discrete
- **OS:** Ubuntu 22.04

## Tech Stack
- **Language:** Python 3.10+
- **TUI Library:** Rich (for beautiful terminal UI)
- **System Interface:** sysfs, asusctl, ryzenadj

## Project Structure
```
rog-control/
├── CLAUDE.md              # This file - AI context
├── README.md              # User documentation
├── .gitignore
├── requirements.txt       # Python dependencies
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py        # Main TUI application
│   │   ├── widgets.py    # Custom UI components
│   │   └── themes.py     # Color themes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cpu.py        # CPU frequency control
│   │   ├── power.py      # RyzenAdj power management
│   │   ├── fans.py       # Fan control via asusctl
│   │   ├── sensors.py    # Temperature/power readings
│   │   └── gpu.py        # GPU control
│   └── utils/
│       ├── __init__.py
│       ├── config.py     # User configuration
│       └── helpers.py    # Utility functions
├── context/
│   ├── ARCHITECTURE.md   # System architecture
│   ├── RYZENADJ.md       # RyzenAdj options reference
│   ├── SYSFS_PATHS.md    # Linux sysfs paths
│   └── TODO.md           # Current tasks
└── docs/
    └── INSTALL.md        # Installation guide
```

## Key System Paths
```python
# Fan control
FAN1_PATH = "/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan1_input"
FAN2_PATH = "/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan2_input"
THERMAL_POLICY = "/sys/devices/platform/asus-nb-wmi/throttle_thermal_policy"

# CPU frequency
CPU_FREQ_PATH = "/sys/devices/system/cpu/cpu{n}/cpufreq/"
SCALING_MAX = "scaling_max_freq"
SCALING_CUR = "scaling_cur_freq"
CPUINFO_MAX = "cpuinfo_max_freq"  # 5263000 (5.26 GHz)

# AMD GPU (integrated)
AMDGPU_PATH = "/sys/class/drm/card1/device/"
```

## External Tools
1. **asusctl** - ASUS laptop control (fans, profiles, RGB)
2. **ryzenadj** - AMD Ryzen power management
3. **sensors** - lm-sensors for temperature readings

## RyzenAdj Key Parameters
All values in milliwatts (mW) or milliamps (mA):
- `--stapm-limit` - Sustained power limit
- `--fast-limit` - Short burst power limit
- `--slow-limit` - Average power limit
- `--tctl-temp` - Temperature limit (°C)
- `--vrm-current` - VRM current limit
- `--vrmmax-current` - VRM max current
- `--max-gfxclk` - Max iGPU clock (MHz)
- `--min-gfxclk` - Min iGPU clock (MHz)

## Design Principles
1. **Real-time updates** - Show live stats with smooth animations
2. **Safe defaults** - Never allow dangerous settings without warning
3. **Keyboard-driven** - Full keyboard navigation, vim-style where possible
4. **Beautiful UI** - Use Rich library for colors, tables, progress bars
5. **Modular** - Each subsystem in its own module

## Current Systemd Services
- `cpu-freq-limit.service` - Caps CPU at 3.0 GHz on boot
- `ryzenadj.service` - Sets 45W power limit on boot
- `asusd.service` - Manages fan profiles

## Coding Standards
- Use type hints
- Docstrings for all public functions
- Handle errors gracefully with user-friendly messages
- No hardcoded passwords or secrets
- Use constants for magic numbers

## Author
Deepak
