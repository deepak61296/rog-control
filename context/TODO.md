# ROG Control - Development TODO

## Current Sprint

### High Priority
- [x] Basic TUI with status display
- [x] CPU frequency control
- [x] Power limit control (basic)
- [x] Fan profile switching
- [x] **Rich library integration for better UI**
- [x] **Real-time monitoring with live updates**
- [x] **GPU stats display (power, temp, clock)**
- [x] **Advanced RyzenAdj controls**
- [x] **Sparkline history graphs**
- [x] **Non-blocking keyboard input**
- [x] **Background threaded data collection**
- [x] **Passwordless sudo for ryzenadj**

### Medium Priority
- [ ] Configuration file for saving presets
- [ ] Per-core frequency display
- [ ] Battery stats and charge limit control
- [ ] Custom preset creation and saving
- [ ] Keyboard shortcuts help panel
- [ ] VRM current limits control
- [ ] Temperature limit control

### Low Priority
- [ ] System tray indicator (separate GTK app)
- [ ] Keyboard RGB control
- [ ] Auto-profile switching based on workload
- [ ] Logging and history
- [ ] Export/import settings

## Bugs
- [ ] hwmon paths may change between boots (need auto-detection)

## Technical Debt
- [ ] Add proper error handling throughout
- [ ] Add type hints to all functions
- [ ] Write unit tests for core modules
- [ ] Add logging

## Ideas for Future
- Curve optimizer integration
- Undervolting support (if unlocked)
- Benchmark mode with stats recording
- Temperature graphs over time
- Discord/webhook notifications for thermal events
- Scheduled profile switching
