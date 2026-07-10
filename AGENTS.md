# ROG Control Agent Guide

## Project Snapshot

ROG Control is a Python 3.10+ Textual TUI for monitoring and safely controlling ASUS ROG laptops on Linux. It reads telemetry from sysfs and command backends, and controls CPU frequency, RyzenAdj power presets, ASUS profiles, and fan curves.

Target environment:
- ASUS ROG Zephyrus G14 class laptop
- Ubuntu/Linux with `asus-wmi`
- Optional write backends: `asusctl`, `asusd`, `ryzenadj`, and `sudo`

## Architecture

- `src/main.py`: CLI entrypoint, `--no-sudo`, startup sudo priming, and sudo keepalive.
- `src/ui/app.py`: Textual app, dashboard panels, keyboard bindings, buttons, confirmation modal, and UI refresh.
- `src/ui/widgets.py`: custom monitoring widgets — `BrailleGraph` (nvtop-style multi-series scrolling line chart), `GaugeBar`, and the per-core load strip. Graph rendering lives in the pure `build_braille_graph` for testability.
- `src/ui/actions.py`: typed control actions and hardware action sequencing.
- `src/ui/collector.py`: background telemetry polling and thread-safe `AppState` snapshots (histories are `HISTORY_LENGTH` samples).
- `src/ui/state.py`: UI state dataclass.
- `src/core/sensors.py`: sysfs and `nvidia-smi` telemetry, including per-core `/proc/stat` utilization, `/proc/meminfo`, and AMD iGPU busy percent. Parsers are pure functions (`parse_proc_stat`, `parse_meminfo`, `utilization_percent`).
- `src/core/cpu.py`: CPU frequency reads and writes.
- `src/core/power.py`: RyzenAdj discovery, telemetry parsing, and power presets. `apply_custom` clamps to `*_BOUNDS` in both directions.
- `src/core/fans.py`: `asusctl` profile and fan curve control.
- `src/core/profile.py`: validated persistent profile storage under `/etc/rog-control/profile.json`.
- `src/core/process.py`: subprocess wrapper with timeout/process-group cleanup.
- `src/daemon.py`: root daemon that reapplies the saved profile after boot and when the profile changes. Includes `ThermalWatchdog` (forces the `cool` power preset after sustained CPU overtemp, latched until cooldown or profile change) and refuses profile files not exclusively owned by root.

The UI should not read sysfs or call vendor tools directly. Add or change hardware operations in `src/core/*`, expose user-triggered operations through `src/ui/actions.py`, and render results from `AppState`.

## Safety Rules

- Keep preset limits conservative unless explicitly asked otherwise.
- Do not add 80W/max RyzenAdj presets or 5.26 GHz CPU presets without an explicit request.
- `PowerController.apply_custom` must clamp all values to the `*_BOUNDS` class constants (both directions); never widen the bounds without an explicit request.
- The daemon `ThermalWatchdog` only ever acts in the safe direction (reducing power). Do not make it raise limits or auto-restore.
- `install_nopasswd.sh` must never emit sudoers wildcards for paths or ryzenadj arguments — sudoers `*` matches `/` and `..`, which is a local privilege escalation. Enumerate explicit paths/commands and validate with `visudo -cf` before installing.
- Keep confirmations for 55W+ power, max fan mode, and performance quick preset.
- Never allow interactive sudo prompts inside the running TUI.
- Sudo-backed commands must use `start_new_session=False` so startup `sudo -v` caching works.
- Unsupported capabilities should disable controls before execution, not fail late after a click.
- Long-running hardware writes must not run on the Textual UI path.

Current presets:
- CPU: 2.5, 3.0, 3.5, 4.0, 4.5 GHz caps; Ultra Battery Saver Quick preset uses 1.5 GHz.
- Power: Silent 15W, Battery 25W, PD 20W, AC 30W, Eco 25W, Cool 35W, Balanced 45W, Performance 55W, High 65W.
- Fan curves: Aggressive and Max.
- Quick presets: Ultra Battery Saver, Battery Saver, Battery Performance, PD Productivity, OEM Performance.

## TUI Behavior

- Textual handles keyboard, mouse, scroll, resize, and modal behavior.
- Keyboard shortcuts: `1` CPU, `2` Power, `3` Fans, `4` Quick, `b` close controls, `Esc` close controls or exit, `Ctrl+C` quit.
- The command palette is disabled; keep the footer focused on app shortcuts only.
- Buttons and keyboard shortcuts must route through the same `ControlAction` execution path.
- Keep action execution single-flight: if one control action is running, disable other action buttons.
- Keep the dashboard useful when backends are unavailable by showing warning state instead of fake telemetry.

## Development Commands

Install:

```bash
python -m pip install -e '.[dev]'
```

Run:

```bash
rog
rog --no-sudo
```

Verify:

```bash
python -m compileall -q src tests
python -m pytest -q
python - <<'PY'
import asyncio
from src.ui.app import RogControlApp

async def main():
    app = RogControlApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
    print("textual pilot ok")

asyncio.run(main())
PY
```

The existing `tests/test_textual_app.py` test covers the same pilot path through pytest.

## Testing Expectations

- Add unit tests for core parsers, subprocess behavior, and action sequencing.
- Add Textual pilot tests for keyboard/button workflows when changing UI behavior.
- Mock hardware commands and sysfs paths in tests; do not require real ASUS hardware or root.
- Run the full verification commands before handing off changes.

## Repository Notes

- `README.md` is user-facing documentation.
- `AGENTS.md` is the canonical agent/developer context. Do not recreate the old `context/` directory or `CLAUDE.md`.
- Generated caches such as `__pycache__/` and egg-info files should not be edited intentionally.
