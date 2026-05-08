#!/usr/bin/env python3
"""WebSocket bridge server for ROG Control Electron UI.

Reuses existing core modules unchanged. Streams telemetry snapshots
over WebSocket and accepts command messages for hardware control.
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from pathlib import Path
from dataclasses import asdict
from typing import Any

# Add project root to sys.path so 'src' package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import websockets

from src.core.sensors import SensorReader, SystemSnapshot
from src.core.cpu import CPUController
from src.core.power import PowerController
from src.core.fans import FanController, FanCurve

HOST = "127.0.0.1"
PORT = 9876


def _serialize_snapshot(snapshot: SystemSnapshot) -> dict:
    data = asdict(snapshot)
    data["type"] = "telemetry"
    return data


class RogServer:
    def __init__(self):
        self.sensors = SensorReader()
        self.cpu = CPUController()
        self.power = PowerController()
        self.fans = FanController()

    async def handler(self, ws: WebSocketServerProtocol):
        print(f"Client connected: {ws.remote_address}")
        task = asyncio.create_task(self._telemetry_loop(ws))
        try:
            async for raw in ws:
                await self._handle_command(ws, raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            print(f"Client disconnected: {ws.remote_address}")

    async def _telemetry_loop(self, ws: WebSocketServerProtocol):
        while True:
            try:
                snapshot = self.sensors.get_snapshot()
                power_info = self.power.get_power_info()
                fan_profile, _ = self.fans.get_profile()
                curve_enabled, _ = self.fans.get_fan_curve_enabled()

                payload = _serialize_snapshot(snapshot)
                payload["power_info"] = asdict(power_info)
                payload["fan_profile"] = fan_profile
                payload["custom_curve_enabled"] = curve_enabled
                payload["cpu_cores"] = self.cpu.get_all_core_freqs()

                await ws.send(json.dumps(payload))
            except websockets.ConnectionClosed:
                break
            await asyncio.sleep(1.0)

    async def _handle_command(self, ws: WebSocketServerProtocol, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self._reply(ws, False, "Invalid JSON")
            return

        action = msg.get("action")
        if not action:
            await self._reply(ws, False, "Missing action")
            return

        handlers = {
            "set_cpu_preset": self._cmd_cpu_preset,
            "set_cpu_freq": self._cmd_cpu_freq,
            "set_power_preset": self._cmd_power_preset,
            "set_fan_profile": self._cmd_fan_profile,
            "set_fan_curve": self._cmd_fan_curve,
            "set_quick_preset": self._cmd_quick_preset,
            "get_config": self._cmd_get_config,
        }

        handler = handlers.get(action)
        if handler:
            success, message = handler(msg)
            await self._reply(ws, success, message)
        else:
            await self._reply(ws, False, f"Unknown action: {action}")

    async def _reply(self, ws: WebSocketServerProtocol, success: bool, message: str):
        await ws.send(json.dumps({"type": "result", "success": success, "message": message}))

    def _cmd_cpu_preset(self, msg: dict) -> tuple[bool, str]:
        preset = msg.get("preset", "")
        return self.cpu.set_preset(preset)

    def _cmd_cpu_freq(self, msg: dict) -> tuple[bool, str]:
        freq = msg.get("freq_khz", 3000000)
        return self.cpu.set_max_freq_all(freq)

    def _cmd_power_preset(self, msg: dict) -> tuple[bool, str]:
        preset = msg.get("preset", "")
        return self.power.set_preset(preset)

    def _cmd_fan_profile(self, msg: dict) -> tuple[bool, str]:
        profile = msg.get("profile", "")
        return self.fans.apply_profile_behavior(profile)

    def _cmd_fan_curve(self, msg: dict) -> tuple[bool, str]:
        curve_name = msg.get("curve", "balanced")
        curve = self.fans.FAN_CURVES.get(curve_name)
        if curve is None:
            return False, f"Unknown curve: {curve_name}"
        success, err = self.fans.set_fan_curve(curve)
        if not success:
            return False, err
        return self.fans.enable_custom_curves(enable=True)

    def _cmd_quick_preset(self, msg: dict) -> tuple[bool, str]:
        preset_name = msg.get("name", "")
        presets = {
            "quiet": ("eco", "eco", "Quiet", "quiet"),
            "cool": ("cool", "cool", "Balanced", "balanced"),
            "balanced": ("balanced", "balanced", "Balanced", "balanced"),
            "performance": ("performance", "performance", "Performance", "aggressive"),
            "max": ("max", "max", "Performance", "max"),
        }
        mapping = presets.get(preset_name)
        if not mapping:
            return False, f"Unknown quick preset: {preset_name}"
        cpu_preset, power_preset, fan_profile, curve_name = mapping

        results = [
            self.cpu.set_preset(cpu_preset),
            self.power.set_preset(power_preset),
            self.fans.set_profile(fan_profile),
            self.fans.set_fan_curve(self.fans.FAN_CURVES[curve_name]),
        ]
        # enable custom curves after setting curve
        if results[3][0]:
            results.append(self.fans.enable_custom_curves(enable=True))

        failures = [msg for ok, msg in results if not ok]
        if failures:
            return False, failures[0]
        return True, f"Preset applied: {preset_name}"

    def _cmd_get_config(self, _msg: dict) -> tuple[bool, str]:
        config = {
            "cpu_presets": list(self.cpu.FREQ_PRESETS.keys()),
            "power_presets": list(self.power.POWER_PRESETS.keys()),
            "fan_curves": list(self.fans.FAN_CURVES.keys()),
            "fan_profiles": self.fans.PROFILES,
            "cpu_max_freq": self.cpu.hw_max_freq,
            "cpu_min_freq": self.cpu.hw_min_freq,
        }
        return True, json.dumps(config)


async def main():
    server = RogServer()
    stop = asyncio.Future()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    async with websockets.serve(server.handler, HOST, PORT):
        print(f"ROG Control server: ws://{HOST}:{PORT}")
        await stop

    print("\nServer stopped.")


if __name__ == "__main__":
    asyncio.run(main())