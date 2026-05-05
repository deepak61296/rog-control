# ROG Control

A Rich-based terminal dashboard for monitoring and controlling thermals, fans, and AMD power limits on ASUS ROG laptops running Linux.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)

## Features

- Live CPU, AMD iGPU, NVIDIA dGPU, fan, battery, and NVMe telemetry
- Separate AMD and NVIDIA sections so GPU stats are never conflated
- CPU frequency presets, RyzenAdj power presets, ASUS profile switching, and fan curve presets
- Capability-aware UI that keeps unsupported features visible but clearly marked unavailable
- Professional Rich-based dashboard with compact fallback mode for narrow terminals

## Interface

```
Header: backend health for CPU hwmon, AMD GPU, NVIDIA, RyzenAdj, and ASUSCtl
Row 1: CPU and Cooling panels
Row 2: AMD iGPU and NVIDIA dGPU panels
Row 3: Power and Battery/Status panels
Footer: action shortcuts and the latest command/result message
```

## Requirements

- ASUS ROG laptop with `asus-wmi` kernel module
- Python 3.10+
- `asusctl` and `asusd` daemon
- `ryzenadj` for AMD Ryzen power control
- passwordless `sudo` for write actions if you want preset changes to succeed without prompts

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
# Run the dashboard
rog-control

# Or from the project directory
./rog-control
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `1` | CPU frequency presets |
| `2` | RyzenAdj power presets |
| `3` | ASUS fan profile |
| `4` | Fan curve presets |
| `5` | Quick combined presets |
| `h` | Help |
| `r` | Status refresh hint |
| `q` | Quit |

## Quick Presets

| Preset | CPU | Power | Fans | Use Case |
|--------|-----|-------|------|----------|
| Quiet Work | 2.5 GHz | 15W | Quiet curve | Battery and quiet work |
| Cool Daily | 3.0 GHz | 35W | Balanced curve | General use |
| Balanced | 3.5 GHz | 45W | Balanced curve | Mixed workloads |
| Heavy Load | 4.5 GHz | 55W | Aggressive curve | Sustained heavier tasks |

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
│   ├── main.py           # Entrypoint and TTY guard
│   ├── core/
│   │   ├── cpu.py        # CPU frequency control backend
│   │   ├── power.py      # RyzenAdj backend and power telemetry parsing
│   │   ├── fans.py       # ASUSCtl backend
│   │   └── sensors.py    # Capability-aware telemetry snapshot model
│   └── ui/
│       ├── __init__.py
│       └── app.py        # Rich dashboard, menus, and collector threads
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
- [Rich](https://github.com/Textualize/rich) for terminal rendering
