#!/bin/bash
# ROG G14 CPU Frequency Limiter
# Sets max CPU frequency - can be overridden by TUI

FREQ=${1:-3000000}  # Default 3 GHz

for i in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do
    echo "$FREQ" > "$i" 2>/dev/null
done

echo "CPU max frequency set to $(awk "BEGIN {printf \"%.1f\", $FREQ/1000000}") GHz"
