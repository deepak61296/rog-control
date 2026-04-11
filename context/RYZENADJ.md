# RyzenAdj Reference

## Overview
RyzenAdj is a tool for adjusting power management settings on AMD Ryzen processors.

## Power Limits

### STAPM (Skin Temperature Aware Power Management)
```bash
--stapm-limit=<mW>     # Sustained power limit (default: 80000 = 80W)
--stapm-time=<s>       # Time constant for STAPM
```

### PPT (Package Power Tracking)
```bash
--fast-limit=<mW>      # Short burst power limit (PPT FAST)
--slow-limit=<mW>      # Average power limit (PPT SLOW)
--slow-time=<s>        # Time constant for slow limit
```

### Recommended Presets
| Preset | STAPM | Fast | Slow | Use Case |
|--------|-------|------|------|----------|
| Silent | 15W | 20W | 15W | Battery, quiet |
| Eco | 25W | 35W | 25W | Light tasks |
| Cool | 35W | 45W | 35W | General use |
| Balanced | 45W | 55W | 45W | Mixed workloads |
| Performance | 65W | 75W | 65W | Heavy tasks |
| Max | 80W | 80W | 80W | Benchmarks |

## Temperature Limits
```bash
--tctl-temp=<°C>       # CPU temperature limit (default: 95)
--apu-skin-temp=<°C>   # APU skin temperature limit
--dgpu-skin-temp=<°C>  # dGPU skin temperature limit
```

## Current Limits (VRM)
```bash
--vrm-current=<mA>     # TDC limit VDD (default: 70000 = 70A)
--vrmsoc-current=<mA>  # TDC limit SoC (default: 18000 = 18A)
--vrmmax-current=<mA>  # EDC limit VDD (default: 140000 = 140A)
--vrmsocmax-current=<mA>  # EDC limit SoC (default: 26000 = 26A)
```

## Clock Frequencies
```bash
--max-gfxclk=<MHz>     # Maximum iGPU clock
--min-gfxclk=<MHz>     # Minimum iGPU clock
--max-socclk-frequency=<MHz>  # Max SoC clock
--min-socclk-frequency=<MHz>  # Min SoC clock
--max-fclk-frequency=<MHz>    # Max fabric clock
--min-fclk-frequency=<MHz>    # Min fabric clock
```

## Performance Modes
```bash
--power-saving         # Optimize for battery life
--max-performance      # Optimize for performance
```

## Reading Current Values
```bash
sudo ryzenadj -i       # Show current power metrics
sudo ryzenadj --dump-table  # Show full power table
```

## Example Commands
```bash
# Cool and quiet
sudo ryzenadj --stapm-limit=35000 --fast-limit=45000 --slow-limit=35000 --tctl-temp=80

# Balanced
sudo ryzenadj --stapm-limit=45000 --fast-limit=55000 --slow-limit=45000

# Max performance
sudo ryzenadj --stapm-limit=80000 --fast-limit=80000 --slow-limit=80000 --tctl-temp=95

# Limit iGPU power
sudo ryzenadj --max-gfxclk=1500 --min-gfxclk=400
```

## Important Notes
1. All power values are in milliwatts (mW)
2. All current values are in milliamps (mA)
3. Changes are temporary - reset on reboot
4. Some options may not work on all CPUs
5. Phoenix Point (7040 series) supports most options
