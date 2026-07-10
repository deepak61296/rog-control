# ROG Control

A Textual-based terminal dashboard for monitoring and safely controlling fans, CPU frequency, and power limits on ASUS ROG laptops running Linux.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)

## Features

- Live CPU, AMD iGPU, NVIDIA dGPU, fan, battery, and NVMe telemetry
- CPU frequency presets, RyzenAdj power presets, and fan curve controls
- Capability-aware UI that keeps unsupported features visible but clearly marked unavailable
- Textual UI with clickable controls, keyboard shortcuts, scrolling, and modal confirmations
- Background action worker so hardware commands do not freeze the interface
- Aggressive fan curves by default to keep the Zephyrus G14 cool

## Interface

```
Header: backend health for CPU hwmon, AMD GPU, NVIDIA, RyzenAdj, and asusctl
Dashboard: CPU, Cooling, AMD iGPU, NVIDIA dGPU, Power, and Battery panels
Controls: clickable CPU, power, fans, and quick preset actions
Status: current CPU cap, power limit, fan profile, latest result, and recent warnings
Footer: keyboard shortcuts
```

## Requirements

- ASUS ROG laptop with `asus-wmi` kernel module
- Python 3.10+
- `asusctl` and `asusd` daemon
- `ryzenadj` for AMD Ryzen power control
- `sudo` access for CPU frequency and RyzenAdj write actions

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/rog-control.git
cd rog-control

# Install
pip install -e .

# Run from anywhere
rog
```

`rog` prompts for sudo once before the dashboard starts, then keeps that sudo
session fresh while the app is open. This prevents password prompts from
appearing inside the live terminal UI. Use `rog --no-sudo` to run monitor-only
when you do not want to unlock write controls.

### Persistent Profiles

Quick presets are saved under `/etc/rog-control/profile.json`. Install the
sudo rules and boot daemon once to restore the saved profile after reboot:

```bash
sudo bash install_nopasswd.sh
```

The installer configures the daemon for the current checkout location. Run it
again after moving the repository.

### Installing Dependencies

**asusctl (Fan control, profiles)**
```bash
sudo add-apt-repository ppa:luke-nukem/asus
sudo apt update
sudo apt install asusctl
sudo systemctl enable --now asusd
```

**RyzenAdj (Power control)**
```bash
sudo apt install libpci-dev cmake build-essential
git clone https://github.com/FlyGoat/RyzenAdj.git
cd RyzenAdj && mkdir build && cd build
cmake .. && make
sudo make install
```

## Usage

```bash
rog
```

Monitor-only mode:

```bash
rog --no-sudo
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `1` | CPU frequency presets |
| `2` | RyzenAdj power presets |
| `3` | Fans: aggressive, max, and firmware default |
| `4` | Quick combined presets |
| `b` | Close controls |
| `Esc` | Close controls / Quit |
| `Ctrl+C` | Quit |

Mouse clicks and scroll-wheel input are handled by Textual. Risky actions open
a confirmation dialog before any hardware write is attempted.

## Quick Presets

| Key | Preset | CPU | RyzenAdj | ASUS profile | Fans |
|-----|--------|-----|----------|--------------|------|
| 1 | Ultra Battery Saver | 1.5 GHz | 15 / 20 / 15W, 75C | Quiet | Firmware Default |
| 2 | Battery Saver | 2.5 GHz | 15 / 20 / 15W, 75C | Quiet | Firmware Default |
| 3 | Battery Performance | 3.0 GHz | 25 / 30 / 25W, 80C | Balanced | Firmware Default |
| 4 | PD Productivity | 2.5 GHz | 20 / 25 / 20W, 80C | Balanced | Firmware Default |
| 5 | OEM Performance | 3.0 GHz | 30 / 35 / 30W, 85C | Performance | Max |

OEM Performance requires confirmation. Use PD Productivity with USB-C PD adapters; reserve OEM Performance for the ASUS 240W adapter.

## Power Presets (RyzenAdj)

| Preset | STAPM | Fast | Slow | Temp |
|--------|-------|------|------|------|
| Silent | 15W | 20W | 15W | 75°C |
| Eco | 25W | 35W | 25W | 80°C |
| Cool | 35W | 45W | 35W | 85°C |
| Balanced | 45W | 55W | 45W | 90°C |
| Performance | 55W | 65W | 55W | 95°C |

## Fans

| Mode | Behavior |
|------|----------|
| Aggressive | 50% at 30C ramping to 100% at 85C. Default for all presets. |
| Max | 100% always. Confirmation required. |
| Firmware Default | Reset to firmware fan control. |

## Safety Guards

- No 80W power preset or 5.26 GHz CPU preset
- Confirmation dialog before 55W+ power presets
- Confirmation dialog before Max (100%) fan mode
- Confirmation before Performance quick preset
- Esc closes controls or exits app
- Status bar shows current CPU cap + power limit

## Author

Deepak
