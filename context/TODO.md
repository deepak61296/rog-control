# ROG Control - Development TODO

## Current Status
v0.2.0 -- Minimal, safe, bug-free TUI. All dangerous presets removed. Confirmation on risky actions.

## Completed
- [x] Basic TUI with live status display
- [x] CPU frequency control (max 4.0 GHz)
- [x] Power limit control via RyzenAdj (max 55W)
- [x] Fan curve control (Aggressive / Max)
- [x] ASUS profile switching
- [x] Live telemetry with background threads
- [x] AMD iGPU + NVIDIA dGPU read-only telemetry
- [x] Sparkline history graphs
- [x] Non-blocking keyboard input
- [x] Compact mode for narrow terminals
- [x] Confirmation dialogs for risky actions
- [x] Esc key to close menus / quit
- [x] Status bar showing current CPU cap + power limit
- [x] pip installable (`pip install -e .`) with `rog` command

## Bugs Fixed
- [x] hwmon paths auto-detection (explicit fallback)
- [x] `_fmt_temp` and `_fmt_percent` dead conditionals removed
- [x] `raise SystemExit` replaced with `sys.exit()`
- [x] Thread race on state.running switched to threading.Event
- [x] Duplicate formatters consolidated into formatters.py

## Low Priority
- [ ] Configuration file for saving presets
- [ ] Per-core frequency display
- [ ] Custom preset creation
- [ ] VRM current limit controls
- [ ] Temperature limit control
- [ ] Auto-profile switching based on workload
- [ ] Logging and history

## Technical Debt
- [ ] Write unit tests for core modules
