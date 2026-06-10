# ROG Control - Development TODO

## Current Status
v0.4.0 -- Textual migration for stable keyboard/mouse input, clickable controls,
confirmation modals, scroll handling, disabled unsupported controls, and
background hardware action execution.

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
- [x] Severity-coloured panel borders (temp/load driven)
- [x] ASCII art block-character header logo
- [x] Temperature gradient bars (per-cell colour interpolation)
- [x] Colour-coded sparkline characters
- [x] Distinct menu border colours per category
- [x] Full compact mini-dashboard with bars and sparklines
- [x] Thread-safety fix in current_state() (deep field copy)
- [x] Capability.last_error removed from Capability model
- [x] DataCollector extracted to src/ui/collector.py
- [x] Menu rendering extracted to src/ui/menus.py
- [x] Shared subprocess helper (src/core/process.py)
- [x] hwmon paths cached (no re-scan every poll)
- [x] Logging infrastructure (stderr, WARNING level)
- [x] nvidia-smi locale fix (LC_ALL=C)
- [x] Dead src/utils/ package removed
- [x] Textual UI migration
- [x] Clickable control buttons
- [x] Scroll-wheel handled by the TUI framework
- [x] Background worker for hardware write actions
- [x] Disabled controls for unavailable backends
- [x] Action-layer tests for control sequencing

## Bugs Fixed
- [x] hwmon paths auto-detection (explicit fallback)
- [x] `_fmt_temp` and `_fmt_percent` dead conditionals removed
- [x] `raise SystemExit` replaced with `sys.exit()`
- [x] Thread race on state.running switched to threading.Event
- [x] Duplicate formatters consolidated into formatters.py
- [x] Thread safety: current_state() now deep-copies mutable dataclass fields
- [x] Capability.last_error removed — controllers now own error state
- [x] Duplicated error recording replaced with _record_error() calls
- [x] Subprocess timeout now kills child via process group
- [x] Thread join timeout increased from 0.2s to 2.0s
- [x] nvidia-smi output parsed with LC_ALL=C locale
- [x] Raw terminal escape parsing removed from the main TUI
- [x] Hardware commands no longer run directly inside key handlers
- [x] Sudo-backed commands keep the current terminal session so startup `sudo -v` caching works
- [x] Quit binding moved to Ctrl+C

## Low Priority
- [ ] Configuration file for saving presets
- [ ] Per-core frequency display
- [ ] Custom preset creation
- [ ] VRM current limit controls
- [ ] Temperature limit control
- [ ] Auto-profile switching based on workload
- [ ] Logging and history

## Technical Debt
- [ ] Add Textual pilot tests once Textual is available in the test environment
- [ ] Broaden unit tests for core modules
