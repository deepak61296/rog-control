# ROG Control - Architecture

## Overview

The application is a Rich-based terminal dashboard with a small core-backend layer:

```text
src/main.py
  -> src/ui/app.py
      -> background collectors
      -> Rich dashboard + menus
      -> action handlers
  -> src/core/sensors.py
  -> src/core/cpu.py
  -> src/core/power.py
  -> src/core/fans.py
```

The UI never talks to sysfs or vendor tools directly. It only renders typed snapshots and action results.

## Runtime Model

### UI layer

`src/ui/app.py` owns:

- terminal setup and key handling
- the live Rich layout
- menu routing for CPU, power, fan profile, fan curve, and quick presets
- background collection threads
- status and error messaging

### Core layer

`src/core/sensors.py` owns:

- hwmon autodiscovery
- CPU telemetry
- AMD iGPU telemetry
- NVIDIA dGPU telemetry via `nvidia-smi`
- battery and fan RPM reads
- capability-aware `SystemSnapshot` objects

`src/core/cpu.py` owns:

- CPU max-frequency reads and writes
- preset frequency caps
- governor discovery and updates

`src/core/power.py` owns:

- `ryzenadj` discovery
- power table parsing
- preset application for STAPM/Fast/Slow/Tctl
- last-error reporting for failed backend calls

`src/core/fans.py` owns:

- `asusctl` discovery
- active profile reads
- custom fan curve enablement
- curve preset and profile writes
- last-error reporting for failed backend calls

## Snapshot Contract

The UI renders one `SystemSnapshot` at a time. The snapshot separates:

- CPU telemetry
- AMD iGPU telemetry
- NVIDIA dGPU telemetry
- cooling telemetry
- battery telemetry
- capability flags and collection errors

This separation prevents the old bug where generic `gpu_*` fields mixed integrated and discrete GPU data.

## Error Handling

- Missing hardware or binaries are represented as unavailable capabilities, not fake zeroes.
- Backend command failures are surfaced as user-visible status and warning text.
- Transient backend failures do not permanently disable retry attempts during the session.
- Narrow terminals fall back to a compact summary view instead of rendering a broken dashboard.
