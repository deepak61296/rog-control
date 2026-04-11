# Linux sysfs Paths Reference

## ASUS WMI Interface
```
/sys/devices/platform/asus-nb-wmi/
├── throttle_thermal_policy    # 0=Performance, 1=Balanced, 2=Quiet
├── charge_mode
├── dgpu_disable
├── gpu_mux_mode
├── panel_od
├── nv_dynamic_boost
├── nv_temp_target
├── ppt_pl1_spl                # Write-only power limits
├── ppt_pl2_sppt
├── ppt_apu_sppt
├── ppt_fppt
└── hwmon/
    ├── hwmon6/                # Fan sensors
    │   ├── fan1_input         # CPU fan RPM
    │   ├── fan1_label
    │   ├── fan2_input         # GPU fan RPM
    │   ├── fan2_label
    │   ├── pwm1_enable        # CPU fan mode
    │   └── pwm2_enable        # GPU fan mode
    └── hwmon7/                # Custom fan curves
        ├── pwm1_enable
        ├── pwm1_auto_point{1-8}_pwm
        ├── pwm1_auto_point{1-8}_temp
        ├── pwm2_enable
        ├── pwm2_auto_point{1-8}_pwm
        └── pwm2_auto_point{1-8}_temp
```

## CPU Frequency
```
/sys/devices/system/cpu/
├── cpu0/cpufreq/
│   ├── scaling_cur_freq       # Current frequency (kHz)
│   ├── scaling_max_freq       # Max allowed frequency (kHz)
│   ├── scaling_min_freq       # Min allowed frequency (kHz)
│   ├── cpuinfo_max_freq       # Hardware max (5263000 = 5.26 GHz)
│   ├── cpuinfo_min_freq       # Hardware min
│   ├── scaling_governor       # powersave, performance, schedutil
│   └── scaling_available_governors
├── cpu1/cpufreq/
│   └── ...
└── cpuN/cpufreq/
    └── ...
```

## hwmon Sensors (lm-sensors)
```
/sys/class/hwmon/
├── hwmon0/name: ADP0          # AC adapter
├── hwmon1/name: acpitz        # ACPI thermal zone
├── hwmon2/name: BAT0          # Battery
├── hwmon3/name: nvme          # NVMe SSD temp
├── hwmon4/name: ucsi_source   # USB-C
├── hwmon5/name: k10temp       # AMD CPU temp
│   └── temp1_input            # Tctl temperature (millidegrees)
├── hwmon6/name: asus          # ASUS fans
├── hwmon7/name: asus_custom_fan_curve
├── hwmon8/name: mt7921_phy0   # WiFi
└── hwmon9/name: amdgpu        # AMD GPU
    ├── temp1_input            # edge temp
    ├── power1_average         # GPU power (microwatts)
    └── freq1_input            # GPU clock
```

## AMD GPU (amdgpu)
```
/sys/class/drm/card1/device/
├── power_dpm_state            # battery, balanced, performance
├── power_dpm_force_performance_level  # auto, low, high, manual
├── pp_power_profile_mode      # Power profiles
├── gpu_busy_percent           # GPU utilization
├── mem_busy_percent           # VRAM utilization
└── hwmon/hwmon9/
    ├── power1_average         # Current power (microwatts)
    ├── power1_cap             # Power limit
    ├── power1_cap_max         # Max power limit
    ├── temp1_input            # Temperature
    └── freq1_input            # Clock speed
```

## NVIDIA GPU (if present)
```
# Use nvidia-smi for NVIDIA stats
nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.gr --format=csv
```

## Battery
```
/sys/class/power_supply/BAT0/
├── status                     # Charging, Discharging, Full
├── capacity                   # Percentage
├── power_now                  # Current power draw (microwatts)
├── voltage_now                # Voltage (microvolts)
├── current_now                # Current (microamps)
└── charge_control_end_threshold  # Charge limit (via asusctl)
```

## Reading Values in Python
```python
def read_sysfs(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except (IOError, PermissionError):
        return None

def write_sysfs(path: str, value: str) -> bool:
    try:
        with open(path, 'w') as f:
            f.write(str(value))
        return True
    except (IOError, PermissionError):
        return False

# Examples
cpu_temp = int(read_sysfs('/sys/class/hwmon/hwmon5/temp1_input')) / 1000
fan_rpm = int(read_sysfs('/sys/devices/platform/asus-nb-wmi/hwmon/hwmon6/fan1_input'))
gpu_power = int(read_sysfs('/sys/class/hwmon/hwmon9/power1_average')) / 1000000
```
