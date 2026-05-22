# ROG Control - AI Agent Context

## Project Overview
ROG Control is a terminal UI for monitoring and safely controlling fans, CPU frequency, and power limits on ASUS ROG laptops running Linux.

## Target Device
- **Model:** ASUS ROG Zephyrus G14 (2023)
- **CPU:** AMD Ryzen 7040 series (Phoenix Point)
- **OS:** Ubuntu 22.04+

## Tech Stack
- **Language:** Python 3.10+
- **TUI:** Rich
- **System Interface:** sysfs, asusctl, ryzenadj

## Project Structure
```
rog-control/
├── CLAUDE.md              # This file
├── README.md              # User documentation
├── pyproject.toml         # Pip install config (rog command)
├── requirements.txt       # Dependencies
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── core/
│   │   ├── cpu.py        # CPU frequency control
│   │   ├── power.py      # RyzenAdj power management
│   │   ├── fans.py       # Fan control via asusctl
│   │   └── sensors.py    # Temperature/power readings
│   ├── ui/
│   │   ├── app.py        # Main TUI application
│   │   ├── formatters.py # Formatting helpers
│   │   └── theme.py      # Color themes
│   └── utils/
│       └── __init__.py
├── context/
│   ├── ARCHITECTURE.md
│   ├── RYZENADJ.md
│   ├── SYSFS_PATHS.md
│   └── TODO.md
└── docs/
```

## Key System Paths
```python
FAN1_PATH = "/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan1_input"
FAN2_PATH = "/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan2_input"
THERMAL_POLICY = "/sys/devices/platform/asus-nb-wmi/throttle_thermal_policy"
SCALING_MAX = "scaling_max_freq"
```

## External Tools
1. **asusctl** - ASUS laptop control (fans, profiles)
2. **ryzenadj** - AMD Ryzen power management

## RyzenAdj Key Parameters
All values in milliwatts:
- `--stapm-limit` - Sustained power limit (max 55000)
- `--fast-limit` - Short burst power limit
- `--slow-limit` - Average power limit
- `--tctl-temp` - Temperature limit (°C)

## Design Principles
1. **Minimal and safe** - No dangerous presets, confirmations on risky actions
2. **Fans always high** - Aggressive fan curve is default for all presets
3. **Safe max values** - CPU capped at 4.0 GHz, power capped at 55W
4. **Real-time updates** - Live telemetry updates every 1-2s
5. **Keyboard-driven** - Full keyboard navigation

## Presets
- CPU: Silent(2.5) / Cool(3.0) / Balanced(3.5) / Performance(4.0) GHz
- Power: Silent(15W) / Eco(25W) / Cool(35W) / Balanced(45W) / Performance(55W)
- Fan curves: Aggressive / Max (100%)
- Quick: Default(2.5GHz+15W+Aggressive) / Balanced(3.5GHz+35W+Aggressive) / Performance(4.0GHz+55W+Max)

## Safety Guards
- No 80W or 5.26 GHz presets
- Confirmations on Performance power, Max fans
- Esc closes menus or exits app
- status bar shows current CPU cap + power limit

## Author
Deepak
