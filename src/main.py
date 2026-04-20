#!/usr/bin/env python3
"""
ROG Control - ASUS ROG Laptop Thermal Management TUI
By Deepak
"""

import os
import sys
import time
import threading
import curses
from typing import Optional
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.sensors import SensorReader, SystemStats
from src.core.cpu import CPUController
from src.core.power import PowerController, PowerInfo
from src.core.fans import FanController


@dataclass
class AppState:
    stats: Optional[SystemStats] = None
    power_info: Optional[PowerInfo] = None
    fan_profile: str = "Unknown"
    message: str = ""
    message_time: float = 0
    cpu_temp_history: list = field(default_factory=list)
    gpu_temp_history: list = field(default_factory=list)


class DataCollector:
    def __init__(self, state: AppState):
        self.state = state
        self.sensors = SensorReader()
        self.cpu = CPUController()
        self.power = PowerController()
        self.fans = FanController()
        self.running = True

        threading.Thread(target=self._collect_sensors, daemon=True).start()
        threading.Thread(target=self._collect_power, daemon=True).start()
        threading.Thread(target=self._collect_profile, daemon=True).start()

    def _collect_sensors(self):
        while self.running:
            try:
                self.state.stats = self.sensors.get_all_stats()
                if self.state.stats:
                    self.state.cpu_temp_history.append(self.state.stats.cpu_temp)
                    self.state.gpu_temp_history.append(self.state.stats.gpu_temp)
                    self.state.cpu_temp_history = self.state.cpu_temp_history[-30:]
                    self.state.gpu_temp_history = self.state.gpu_temp_history[-30:]
            except: pass
            time.sleep(0.5)

    def _collect_power(self):
        while self.running:
            try:
                info = self.power.get_power_info()
                if info.stapm_limit > 0:
                    self.state.power_info = info
            except: pass
            time.sleep(2)

    def _collect_profile(self):
        while self.running:
            try:
                self.state.fan_profile = self.fans.get_profile()
            except: pass
            time.sleep(5)

    def stop(self):
        self.running = False


def make_bar(value, max_val, width=20):
    if max_val <= 0:
        return "─" * width
    pct = min(1.0, max(0, value / max_val))
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


def make_sparkline(history, width=15):
    if not history:
        return "─" * width
    chars = "▁▂▃▄▅▆▇█"
    recent = history[-width:]
    if len(recent) < 2:
        return "─" * width
    mn, mx = min(recent), max(recent)
    rng = mx - mn if mx > mn else 1
    return "".join(chars[min(7, int((v - mn) / rng * 7))] for v in recent).rjust(width, "─")


def temp_color(temp):
    if temp < 50: return 1  # green
    elif temp < 70: return 3  # yellow
    elif temp < 85: return 2  # red
    else: return 2  # red


def draw_box(win, y, x, h, w, title=""):
    """Draw a box with title"""
    # Corners and lines
    win.addstr(y, x, "┌" + "─" * (w - 2) + "┐")
    for i in range(1, h - 1):
        win.addstr(y + i, x, "│" + " " * (w - 2) + "│")
    win.addstr(y + h - 1, x, "└" + "─" * (w - 2) + "┘")
    if title:
        win.addstr(y, x + 2, f" {title} ", curses.A_BOLD)


def draw_dashboard(stdscr, state: AppState, frame: int):
    h, w = stdscr.getmaxyx()
    stdscr.clear()

    # Check minimum terminal size
    MIN_WIDTH = 78
    MIN_HEIGHT = 22
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        stdscr.addstr(0, 0, f"Terminal too small! Need {MIN_WIDTH}x{MIN_HEIGHT}, got {w}x{h}", curses.A_BOLD | curses.color_pair(2))
        stdscr.addstr(2, 0, "Please resize your terminal window and try again.", curses.A_DIM)
        stdscr.addstr(4, 0, "Press 'q' to quit.", curses.A_DIM)
        stdscr.refresh()
        return

    # Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)

    spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[frame % 10]

    # Header
    title = f"  ⚡ ROG CONTROL ⚡  {spinner}"
    stdscr.addstr(0, (w - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(4))

    s = state.stats
    p = state.power_info

    # === TEMPERATURES ===
    draw_box(stdscr, 2, 1, 7, 40, "🌡️ TEMPERATURES")
    if s:
        # CPU
        stdscr.addstr(3, 3, "CPU  ", curses.A_BOLD)
        stdscr.addstr(3, 8, f"{s.cpu_temp:5.1f}°C ", curses.color_pair(temp_color(s.cpu_temp)))
        stdscr.addstr(3, 18, make_bar(s.cpu_temp, 100, 12))
        stdscr.addstr(3, 31, make_sparkline(state.cpu_temp_history, 8))

        # GPU
        stdscr.addstr(4, 3, "GPU  ", curses.A_BOLD)
        stdscr.addstr(4, 8, f"{s.gpu_temp:5.1f}°C ", curses.color_pair(temp_color(s.gpu_temp)))
        stdscr.addstr(4, 18, make_bar(s.gpu_temp, 100, 12))
        stdscr.addstr(4, 31, make_sparkline(state.gpu_temp_history, 8))

        # SSD
        stdscr.addstr(5, 3, "SSD  ", curses.A_BOLD)
        stdscr.addstr(5, 8, f"{s.nvme_temp:5.1f}°C ", curses.color_pair(temp_color(s.nvme_temp)))
        stdscr.addstr(5, 18, make_bar(s.nvme_temp, 80, 12))
    else:
        stdscr.addstr(4, 3, "Loading...", curses.A_DIM)

    # === FANS ===
    draw_box(stdscr, 2, 42, 7, 35, "🌀 FANS")
    if s:
        stdscr.addstr(3, 44, "CPU  ", curses.A_BOLD)
        stdscr.addstr(3, 49, f"{s.cpu_fan_rpm:5d} RPM ", curses.color_pair(4))
        stdscr.addstr(3, 62, make_bar(s.cpu_fan_rpm, 6500, 12))

        stdscr.addstr(4, 44, "GPU  ", curses.A_BOLD)
        stdscr.addstr(4, 49, f"{s.gpu_fan_rpm:5d} RPM ", curses.color_pair(4))
        stdscr.addstr(4, 62, make_bar(s.gpu_fan_rpm, 6500, 12))

        profile = state.fan_profile
        pcolor = 2 if profile == "Performance" else 3 if profile == "Balanced" else 1
        stdscr.addstr(6, 44, "Mode: ", curses.A_DIM)
        stdscr.addstr(6, 50, profile, curses.A_BOLD | curses.color_pair(pcolor))

    # === CPU ===
    draw_box(stdscr, 10, 1, 6, 26, "⚙️ CPU")
    if s:
        cur_ghz = s.cpu_freq_current / 1000
        max_ghz = s.cpu_freq_max / 1000
        stdscr.addstr(11, 3, "Current ", curses.A_DIM)
        stdscr.addstr(11, 11, f"{cur_ghz:.2f} GHz", curses.A_BOLD | curses.color_pair(4))
        stdscr.addstr(12, 3, "Limit   ", curses.A_DIM)
        stdscr.addstr(12, 11, f"{max_ghz:.2f} GHz", curses.color_pair(3))
        stdscr.addstr(13, 3, "HW Max  ", curses.A_DIM)
        stdscr.addstr(13, 11, "5.26 GHz", curses.A_DIM)

    # === POWER (only when no NVIDIA) ===
    if not (s and s.has_nvidia):
        draw_box(stdscr, 10, 28, 7, 30, "⚡ POWER")
        if p and p.stapm_limit > 0:
            stdscr.addstr(11, 30, "STAPM ", curses.A_DIM)
            stdscr.addstr(11, 36, f"{p.stapm_value:5.1f}/{p.stapm_limit:3.0f}W", curses.color_pair(1))
            stdscr.addstr(11, 50, make_bar(p.stapm_value, p.stapm_limit, 6))

            stdscr.addstr(12, 30, "Fast  ", curses.A_DIM)
            stdscr.addstr(12, 36, f"{p.fast_value:5.1f}/{p.fast_limit:3.0f}W", curses.color_pair(3))
            stdscr.addstr(12, 50, make_bar(p.fast_value, p.fast_limit, 6))

            stdscr.addstr(13, 30, "Slow  ", curses.A_DIM)
            stdscr.addstr(13, 36, f"{p.slow_value:5.1f}/{p.slow_limit:3.0f}W", curses.color_pair(3))
            stdscr.addstr(13, 50, make_bar(p.slow_value, p.slow_limit, 6))

            # GPU Power from sensors
            if s:
                stdscr.addstr(14, 30, "iGPU  ", curses.A_DIM)
                stdscr.addstr(14, 36, f"{s.gpu_power:5.1f}W", curses.color_pair(4))
        else:
            stdscr.addstr(12, 30, "Fetching...", curses.A_DIM)

    # === GPU (AMD iGPU) or NVIDIA (dGPU) ===
    if s and s.has_nvidia:
        # NVIDIA dGPU - replaces Power section
        draw_box(stdscr, 10, 28, 8, 30, "🔥 dGPU")
        stdscr.addstr(11, 30, "Temp  ", curses.A_DIM)
        stdscr.addstr(11, 36, f"{s.nvidia_temp:5.1f}°C", curses.color_pair(temp_color(s.nvidia_temp)))
        stdscr.addstr(12, 30, "Power ", curses.A_DIM)
        stdscr.addstr(12, 36, f"{s.nvidia_power:5.1f} W", curses.color_pair(3))
        stdscr.addstr(13, 30, "Clock ", curses.A_DIM)
        stdscr.addstr(13, 36, f"{s.nvidia_clock:4d} MHz", curses.color_pair(4))
        stdscr.addstr(14, 30, "Util   ", curses.A_DIM)
        stdscr.addstr(14, 36, f"{s.nvidia_util:3d}%", curses.color_pair(3))
        stdscr.addstr(14, 40, make_bar(s.nvidia_util, 100, 6))
        stdscr.addstr(15, 30, "VRAM  ", curses.A_DIM)
        stdscr.addstr(15, 36, f"{s.nvidia_vram_used:4d}/{s.nvidia_vram_total:4d}MB", curses.color_pair(4))
        
        # iGPU info on same row as controls
        stdscr.addstr(16, 30, "iGPU   ", curses.A_DIM)
        stdscr.addstr(16, 37, f"{s.gpu_clock:4d}MHz {s.gpu_power:4.1f}W", curses.color_pair(4))
    else:
        # AMD iGPU only
        draw_box(stdscr, 10, 59, 7, 18, "🎮 iGPU")
        if s:
            stdscr.addstr(11, 61, "Clock ", curses.A_DIM)
            stdscr.addstr(11, 67, f"{s.gpu_clock:4d} MHz", curses.color_pair(4))
            stdscr.addstr(12, 61, "Power ", curses.A_DIM)
            stdscr.addstr(12, 67, f"{s.gpu_power:5.1f} W", curses.color_pair(3))
            stdscr.addstr(13, 61, "Temp  ", curses.A_DIM)
            stdscr.addstr(13, 67, f"{s.gpu_temp:5.1f}°C", curses.color_pair(temp_color(s.gpu_temp)))

    # === BATTERY ===
    if s:
        bat_row = 15 if (s and s.has_nvidia) else 15
        bat_str = f"🔋 {s.battery_percent}% ({s.battery_status})"
        bcolor = 1 if s.battery_percent > 50 else 3 if s.battery_percent > 20 else 2
        bat_x = 61 if not (s and s.has_nvidia) else 1
        stdscr.addstr(bat_row, bat_x, bat_str[:16], curses.color_pair(bcolor))

    # === CONTROLS ===
    draw_box(stdscr, 17, 1, 8, 76, "⌨️ CONTROLS")
    stdscr.addstr(18, 3, "[1]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(18, 7, "CPU Freq    ")
    stdscr.addstr(18, 20, "[2]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(18, 24, "Power Limits ")
    stdscr.addstr(18, 40, "[3]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(18, 44, "Fan Profile ")
    stdscr.addstr(18, 58, "[4]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(18, 62, "Fan Curve")

    stdscr.addstr(19, 3, "[5]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(19, 7, "Quick Presets")
    stdscr.addstr(19, 40, "[r]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(19, 44, "Refresh     ")
    stdscr.addstr(19, 58, "[q]", curses.A_BOLD | curses.color_pair(3))
    stdscr.addstr(19, 62, "Quit")

    # Message
    if state.message and time.time() - state.message_time < 3:
        stdscr.addstr(21, 3, state.message, curses.A_BOLD | curses.color_pair(1))
    else:
        stdscr.addstr(21, 3, "Press a key to adjust settings", curses.A_DIM)

    stdscr.refresh()


def cpu_menu(stdscr, cpu: CPUController, state: AppState):
    curses.echo()
    stdscr.clear()
    stdscr.addstr(0, 0, "═══ CPU FREQUENCY ═══", curses.A_BOLD)
    stdscr.addstr(2, 0, f"Current limit: {cpu.get_max_freq()/1000000:.2f} GHz\n")

    options = [
        ("1", 1.5), ("2", 2.0), ("3", 2.5), ("4", 3.0),
        ("5", 3.5), ("6", 4.0), ("7", 4.5), ("8", 5.26)
    ]
    for i, (key, ghz) in enumerate(options):
        stdscr.addstr(4 + i, 0, f"  [{key}] {ghz:.2f} GHz")

    stdscr.addstr(13, 0, "  [c] Custom  [b] Back")
    stdscr.addstr(15, 0, "Select: ")
    stdscr.refresh()

    curses.noecho()
    key = stdscr.getch()
    ch = chr(key).lower() if key < 256 else ''

    freq_map = {"1": 1500000, "2": 2000000, "3": 2500000, "4": 3000000,
                "5": 3500000, "6": 4000000, "7": 4500000, "8": 5263000}

    if ch in freq_map:
        cpu.set_max_freq_all(freq_map[ch])
        state.message = f"✓ CPU set to {freq_map[ch]/1000000:.1f} GHz"
        state.message_time = time.time()
    elif ch == 'c':
        curses.echo()
        stdscr.addstr(16, 0, "Enter GHz: ")
        stdscr.refresh()
        try:
            inp = stdscr.getstr(16, 11, 10).decode()
            ghz = float(inp)
            cpu.set_max_freq_all(int(ghz * 1000000))
            state.message = f"✓ CPU set to {ghz:.1f} GHz"
            state.message_time = time.time()
        except:
            state.message = "Invalid input"
            state.message_time = time.time()
        curses.noecho()


def power_menu(stdscr, power: PowerController, state: AppState):
    stdscr.clear()
    stdscr.addstr(0, 0, "═══ POWER LIMITS ═══", curses.A_BOLD)

    presets = [
        ("1", "Silent", 15, 20, 15),
        ("2", "Eco", 25, 35, 25),
        ("3", "Cool", 35, 45, 35),
        ("4", "Balanced", 45, 55, 45),
        ("5", "Performance", 55, 65, 55),
        ("6", "High", 65, 75, 65),
        ("7", "Maximum", 80, 80, 80),
    ]

    stdscr.addstr(2, 0, "    Preset       STAPM  Fast  Slow")
    for i, (key, name, s, f, sl) in enumerate(presets):
        stdscr.addstr(3 + i, 0, f"  [{key}] {name:12} {s:3}W  {f:3}W  {sl:3}W")

    stdscr.addstr(11, 0, "  [b] Back")
    stdscr.addstr(13, 0, "Select: ")
    stdscr.refresh()

    key = stdscr.getch()
    ch = chr(key).lower() if key < 256 else ''

    preset_map = {"1": "silent", "2": "eco", "3": "cool", "4": "balanced",
                  "5": "performance", "6": "high", "7": "max"}

    if ch in preset_map:
        power.set_preset(preset_map[ch])
        state.message = f"✓ Power preset applied"
        state.message_time = time.time()


def fan_menu(stdscr, fans: FanController, state: AppState):
    stdscr.clear()
    stdscr.addstr(0, 0, "═══ FAN PROFILE ═══", curses.A_BOLD)
    stdscr.addstr(2, 0, f"Current: {state.fan_profile}")

    stdscr.addstr(4, 0, "  [1] Performance")
    stdscr.addstr(5, 0, "  [2] Balanced")
    stdscr.addstr(6, 0, "  [3] Quiet")
    stdscr.addstr(8, 0, "  [b] Back")
    stdscr.addstr(10, 0, "Select: ")
    stdscr.refresh()

    key = stdscr.getch()
    ch = chr(key).lower() if key < 256 else ''

    profiles = {"1": "Performance", "2": "Balanced", "3": "Quiet"}
    if ch in profiles:
        fans.set_profile(profiles[ch])
        state.fan_profile = profiles[ch]
        state.message = f"✓ Profile: {profiles[ch]}"
        state.message_time = time.time()


def fan_curve_menu(stdscr, fans: FanController, state: AppState):
    stdscr.clear()
    stdscr.addstr(0, 0, "═══ FAN CURVE ═══", curses.A_BOLD)

    stdscr.addstr(2, 0, "  [1] Silent     (20-80%)")
    stdscr.addstr(3, 0, "  [2] Quiet      (30-100%)")
    stdscr.addstr(4, 0, "  [3] Balanced   (30-100%)")
    stdscr.addstr(5, 0, "  [4] Aggressive (50-100%)")
    stdscr.addstr(6, 0, "  [5] Maximum    (100%)")
    stdscr.addstr(7, 0, "  [d] Default")
    stdscr.addstr(9, 0, "  [b] Back")
    stdscr.addstr(11, 0, "Select: ")
    stdscr.refresh()

    key = stdscr.getch()
    ch = chr(key).lower() if key < 256 else ''

    curve_map = {"1": "silent", "2": "quiet", "3": "balanced", "4": "aggressive", "5": "max"}

    if ch in curve_map:
        fans.set_fan_curve_preset(curve_map[ch])
        fans.enable_custom_curves(enable=True)
        state.message = f"✓ Fan curve: {curve_map[ch]}"
        state.message_time = time.time()
    elif ch == 'd':
        fans.reset_fan_curve()
        fans.enable_custom_curves(enable=False)
        state.message = "✓ Fan curve reset"
        state.message_time = time.time()


def presets_menu(stdscr, cpu: CPUController, power: PowerController, fans: FanController, state: AppState):
    stdscr.clear()
    stdscr.addstr(0, 0, "═══ QUICK PRESETS ═══", curses.A_BOLD)

    presets = [
        ("1", "Silent", "15W, 2.5GHz, Quiet fans", 2500000, "silent", "Quiet", "silent"),
        ("2", "Cool", "35W, 3.0GHz, Max fans", 3000000, "cool", "Performance", "max"),
        ("3", "Balanced", "45W, 3.5GHz, Max fans", 3500000, "balanced", "Performance", "max"),
        ("4", "Performance", "55W, 4.5GHz, Max fans", 4500000, "performance", "Performance", "max"),
        ("5", "Beast Mode", "80W, 5.26GHz, Max fans", 5263000, "max", "Performance", "max"),
    ]

    for i, (key, name, desc, _, _, _, _) in enumerate(presets):
        stdscr.addstr(2 + i, 0, f"  [{key}] {name:14} {desc}")

    stdscr.addstr(8, 0, "  [b] Back")
    stdscr.addstr(10, 0, "Select: ")
    stdscr.refresh()

    key = stdscr.getch()
    ch = chr(key).lower() if key < 256 else ''

    for pkey, name, _, freq, pwr, profile, fcurve in presets:
        if ch == pkey:
            cpu.set_max_freq_all(freq)
            power.set_preset(pwr)
            fans.set_profile(profile)
            if fcurve == "max":
                fans.set_max_fans()
            else:
                fans.set_fan_curve_preset(fcurve)
                fans.enable_custom_curves(enable=True)
            state.message = f"✓ Applied: {name}"
            state.message_time = time.time()
            break


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(250)

    state = AppState()
    collector = DataCollector(state)

    frame = 0
    running = True

    try:
        while running:
            draw_dashboard(stdscr, state, frame)
            frame += 1

            key = stdscr.getch()
            if key == -1:
                continue

            ch = chr(key).lower() if key < 256 else ''

            if ch == 'q':
                running = False
            elif ch == '1':
                stdscr.nodelay(False)
                cpu_menu(stdscr, collector.cpu, state)
                stdscr.nodelay(True)
                stdscr.timeout(250)
            elif ch == '2':
                stdscr.nodelay(False)
                power_menu(stdscr, collector.power, state)
                stdscr.nodelay(True)
                stdscr.timeout(250)
            elif ch == '3':
                stdscr.nodelay(False)
                fan_menu(stdscr, collector.fans, state)
                stdscr.nodelay(True)
                stdscr.timeout(250)
            elif ch == '4':
                stdscr.nodelay(False)
                fan_curve_menu(stdscr, collector.fans, state)
                stdscr.nodelay(True)
                stdscr.timeout(250)
            elif ch == '5':
                stdscr.nodelay(False)
                presets_menu(stdscr, collector.cpu, collector.power, collector.fans, state)
                stdscr.nodelay(True)
                stdscr.timeout(250)
            elif ch == 'r':
                state.message = "Refreshed!"
                state.message_time = time.time()

    finally:
        collector.stop()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("Goodbye!")
