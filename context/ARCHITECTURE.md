# ROG Control - Architecture

## Overview

The application is a Textual-based terminal dashboard with a small core-backend layer:

```text
src/main.py
  -> src/ui/app.py
      -> background collectors
      -> Textual dashboard + controls
      -> background action worker
  -> src/ui/actions.py
      -> typed hardware control actions
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
- the Textual layout, buttons, scrolling, and confirmation modal
- keyboard shortcuts for CPU, power, fan profile, fan curve, and quick presets
- background collection threads
- status and error messaging

`src/ui/actions.py` owns:

- typed control action definitions
- quick preset sequencing
- current fan profile targeting for fan curve changes
- a single execution path used by buttons and keyboard shortcuts

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
- Unsupported write controls are disabled before the user can trigger them.
- Long-running hardware commands execute in a worker so input, rendering, and scroll handling remain responsive.
