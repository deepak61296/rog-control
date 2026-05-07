"""Configuration management for ROG Control."""

from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any
from pathlib import Path


DEFAULT_CONFIG = {
    "version": "1.0",
    "theme": {
        "primary_color": "#00ff00",
        "secondary_color": "#00cc88",
        "background": "#001108",
    },
    "presets": {
        "cpu": {
            "silent": 2500000,
            "eco": 2500000,
            "cool": 3000000,
            "balanced": 3500000,
            "performance": 4000000,
            "max": 5263000,
        },
        "power": {
            "silent": {"stapm": 15000, "fast": 20000, "slow": 15000, "tctl": 75},
            "eco": {"stapm": 25000, "fast": 35000, "slow": 25000, "tctl": 80},
            "balanced": {"stapm": 45000, "fast": 55000, "slow": 45000, "tctl": 90},
            "performance": {"stapm": 55000, "fast": 65000, "slow": 55000, "tctl": 95},
            "max": {"stapm": 80000, "fast": 80000, "slow": 80000, "tctl": 100},
        },
        "fan_curves": {
            "silent": [(30, 20), (40, 25), (50, 30), (60, 40), (70, 50), (80, 65), (90, 80), (100, 80)],
            "quiet": [(30, 30), (40, 35), (50, 40), (60, 50), (70, 60), (80, 75), (90, 90), (100, 100)],
            "balanced": [(30, 30), (40, 40), (50, 50), (60, 60), (70, 75), (80, 90), (90, 100), (100, 100)],
            "aggressive": [(30, 50), (40, 55), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100), (100, 100)],
            "max": [(30, 100), (40, 100), (50, 100), (60, 100), (70, 100), (80, 100), (90, 100), (100, 100)],
        }
    },
    "last_settings": {
        "cpu_freq_limit": None,
        "power_preset": None,
        "fan_profile": None,
        "fan_curve": None,
    },
    "monitor": {
        "temp_history_length": 60,
        "refresh_interval": 1.0,
        "sparkline_width": 25,
    },
    "paths": {
        "ryzenadj": None,  # Auto-detect
        "asusctl": None,  # Auto-detect
    }
}


class Config:
    """Manages ROG Control configuration file."""

    CONFIG_DIR = Path.home() / ".config" / "rog-control"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def __init__(self):
        self.config = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> bool:
        """Load configuration from file."""
        if not self.CONFIG_FILE.exists():
            return False

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge with defaults to handle new keys
                self._merge_config(self.config, loaded)
                return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
            return False

    def save(self) -> bool:
        """Save configuration to file."""
        try:
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, *keys, default=None):
        """Get a nested config value."""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, *keys, value) -> None:
        """Set a nested config value."""
        config = self.config
        for key in keys[:-1]:
            if key not in config or not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    def save_last_settings(self, **kwargs) -> None:
        """Save last used settings."""
        for key, value in kwargs.items():
            self.set("last_settings", key, value=value)
        self.save()

    def get_last_settings(self) -> Dict[str, Any]:
        """Get last used settings."""
        return self.get("last_settings", default={})

    def _merge_config(self, base: dict, update: dict) -> None:
        """Recursively merge update into base."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def get_default_config_path() -> Path:
        """Return the default config file path."""
        return Config.CONFIG_FILE