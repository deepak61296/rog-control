# ROG Control 🎮⚡

A beautiful terminal UI for controlling thermals, fans, and power on ASUS ROG Zephyrus G14 (2023) laptops running Linux.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)

## Features ✨

- **Real-time Monitoring** - Live CPU/GPU temps, fan speeds, power draw
- **CPU Frequency Control** - Set max frequency limits (1.5-5.26 GHz)
- **Power Management** - Full RyzenAdj integration with presets
- **Fan Control** - Profiles and custom fan curves via asusctl
- **Quick Presets** - One-click thermal profiles (Silent, Cool, Balanced, Beast)
- **Beautiful TUI** - Rich terminal interface with progress bars and colors

## Screenshot

```
╔══════════════════════════════════════════════════════════════════╗
║   ⚡ ROG CONTROL ⚡  ASUS ROG Zephyrus G14                        ║
╚══════════════════════════════════════════════════════════════════╝

┌─ 🌡️ TEMPERATURES ─────┐  ┌─ 🌀 FANS ──────────────┐
│ CPU   82.5°C ████████░░│  │ CPU   5500 RPM ████████│
│ GPU   74.0°C ██████░░░░│  │ GPU   5800 RPM ████████│
│ NVMe  33.8°C ███░░░░░░░│  │ Profile: Performance   │
└────────────────────────┘  └────────────────────────┘

┌─ ⚙️ CPU ────────────┐  ┌─ ⚡ POWER ────────────────┐
│ Current  2.9 GHz    │  │ STAPM  12.5W /45W ██░░░░░│
│ Limit    3.0 GHz    │  │ Fast   15.2W /55W ██░░░░░│
│ Max      5.26 GHz   │  │ Slow   10.8W /45W ██░░░░░│
└─────────────────────┘  └──────────────────────────┘

[1] CPU Frequency  [2] Power Limits  [3] Fan Profile
[4] Fan Curve      [5] Quick Presets [q] Quit
```

## Requirements

- ASUS ROG laptop with `asus-wmi` kernel module
- Python 3.10+
- `asusctl` and `asusd` daemon
- `ryzenadj` for AMD Ryzen power control

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/rog-control.git
cd rog-control

# Install Python dependencies
pip install -r requirements.txt

# Install system-wide (optional)
sudo ln -s $(pwd)/rog-control /usr/local/bin/rog-control

# Run
./rog-control
```

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
# Run the TUI
rog-control

# Or from the project directory
./rog-control
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `1` | CPU Frequency settings |
| `2` | Power Limits (RyzenAdj) |
| `3` | Fan Profile (Performance/Balanced/Quiet) |
| `4` | Custom Fan Curves |
| `5` | Quick Presets |
| `r` | Refresh display |
| `q` | Quit |

## Quick Presets

| Preset | CPU | Power | Fans | Use Case |
|--------|-----|-------|------|----------|
| Silent | 2.5 GHz | 15W | Quiet | Battery, quiet work |
| Cool | 3.0 GHz | 35W | Max | General use |
| Balanced | 3.5 GHz | 45W | Max | Mixed workloads |
| Performance | 4.5 GHz | 55W | Max | Heavy tasks |
| Beast Mode | 5.26 GHz | 80W | Max | Benchmarks (HOT!) |

## Power Presets (RyzenAdj)

| Preset | STAPM | Fast | Slow | Temp |
|--------|-------|------|------|------|
| Silent | 15W | 20W | 15W | 75°C |
| Eco | 25W | 35W | 25W | 80°C |
| Cool | 35W | 45W | 35W | 85°C |
| Balanced | 45W | 55W | 45W | 90°C |
| Performance | 55W | 65W | 55W | 95°C |
| Max | 80W | 80W | 80W | 100°C |

## Auto-start on Boot

Create systemd services for persistent settings:

```bash
# CPU frequency limit
sudo tee /etc/systemd/system/cpu-freq-limit.service << 'EOF'
[Unit]
Description=ROG CPU Frequency Limit
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for i in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do echo 3000000 > "$i"; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# RyzenAdj power limits
sudo tee /etc/systemd/system/ryzenadj.service << 'EOF'
[Unit]
Description=RyzenAdj Power Limits
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/ryzenadj --stapm-limit=45000 --fast-limit=55000 --slow-limit=45000
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cpu-freq-limit ryzenadj
```

## Project Structure

```
rog-control/
├── CLAUDE.md              # AI agent context
├── README.md
├── requirements.txt
├── rog-control            # Launcher script
├── src/
│   ├── main.py           # Main TUI application
│   ├── core/
│   │   ├── cpu.py        # CPU frequency control
│   │   ├── power.py      # RyzenAdj integration
│   │   ├── fans.py       # Fan control via asusctl
│   │   └── sensors.py    # Temperature/power readings
│   └── ui/
│       └── (future UI components)
├── context/
│   ├── ARCHITECTURE.md   # System architecture
│   ├── RYZENADJ.md       # RyzenAdj reference
│   ├── SYSFS_PATHS.md    # Linux sysfs paths
│   └── TODO.md           # Development tasks
└── docs/
    └── (documentation)
```

## Contributing

Pull requests welcome! See `context/TODO.md` for planned features.

## License

MIT

## Author

Deepak

## Acknowledgments

- [asus-linux](https://asus-linux.org/) for asusctl
- [RyzenAdj](https://github.com/FlyGoat/RyzenAdj) for power management
- [Rich](https://github.com/Textualize/rich) for the beautiful TUI
