"""Shared application state dataclass for ROG Control.

Separated from app.py and collector.py to avoid circular imports
when the collector needs to construct safe copies for the render thread.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from src.core.power import PowerInfo
from src.core.sensors import Capability, SystemSnapshot


@dataclass
class AppState:
    snapshot: SystemSnapshot = field(default_factory=SystemSnapshot)
    power_info: PowerInfo = field(default_factory=PowerInfo)
    fan_profile: Optional[str] = None
    custom_curve_enabled: Optional[bool] = None
    cpu_capability: Capability = field(default_factory=lambda: Capability(False, "not initialized"))
    power_capability: Capability = field(default_factory=lambda: Capability(False, "not initialized"))
    fan_capability: Capability = field(default_factory=lambda: Capability(False, "not initialized"))
    cpu_error: str = ""
    power_error: str = ""
    fan_error: str = ""
    message: str = "Press h for help."
    message_style: str = "cyan"
    message_time: float = field(default_factory=time.time)
    active_menu: Optional[str] = None
    pending_confirm: Optional[str] = None
    cpu_temp_history: list[float] = field(default_factory=list)
    amd_gpu_temp_history: list[float] = field(default_factory=list)
    cpu_util_history: list[float] = field(default_factory=list)
    gpu_util_history: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
