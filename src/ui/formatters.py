"""Centralized formatting and chart helpers for rog-control.

Merges formatting functions previously duplicated across ``app.py`` and
``charts.py`` into one place.  Every UI component should import from here
rather than redefining its own formatters.
"""

from __future__ import annotations

from typing import Optional

from rich.text import Text

from src.ui.theme import (
    BAR_EMPTY,
    BAR_FILL,
    DIM,
    HEALTHY,
    HOT,
    SPARKLINE_CHARS,
    WARN,
    battery_severity as BATTERY_SEVERITY,
    ratio_severity as RATIO_SEVERITY,
    temp_severity as TEMP_SEVERITY,
)


# ── Plain-text formatters (no colour) ────────────────────────────────

def fmt_temp(value: Optional[float]) -> str:
    if value is None:
        return "---"
    return f"{value:.0f}\u00b0C"


def fmt_power(value: Optional[float]) -> str:
    if value is None:
        return "---"
    return f"{value:.1f} W"


def fmt_freq(value: Optional[int]) -> str:
    if value is None:
        return "---"
    return f"{value / 1000:.2f} GHz"


def fmt_rpm(value: Optional[int]) -> str:
    if value is None:
        return "---"
    return f"{value} RPM"


def fmt_percent(value: Optional[int]) -> str:
    if value is None:
        return "---"
    return f"{value}%"


def fmt_gb(value_mb: Optional[int]) -> str:
    if value_mb is None:
        return "---"
    return f"{value_mb / 1024:.1f}"


def fmt_vram(used: Optional[int], total: Optional[int]) -> str:
    if used is None or total is None:
        return "---"
    return f"{used / 1024:.1f}/{total / 1024:.1f}"


# ── Coloured Text formatters (with severity) ─────────────────────────

def coloured_temp(value: Optional[float]) -> Text:
    if value is None:
        return Text("---", style=DIM)
    return Text(f"{value:.0f}\u00b0C", style=TEMP_SEVERITY(value))


def coloured_freq(value: Optional[int]) -> Text:
    if value is None:
        return Text("---", style=DIM)
    return Text(f"{value / 1000:.2f} GHz")


def coloured_power(value: Optional[float]) -> Text:
    if value is None:
        return Text("---", style=DIM)
    return Text(f"{value:.1f} W")


def coloured_percent(value: Optional[int]) -> Text:
    if value is None:
        return Text("---", style=DIM)
    style = RATIO_SEVERITY((value or 0) / 100.0)
    return Text(f"{value}%", style=style)


# ── Sparkline (colour-coded per value) ───────────────────────────────

def sparkline(values: list[float], width: int = 12) -> Text:
    """Unicode sparkline of recent values."""
    if len(values) < 2:
        return Text(" " * width)
    recent = values[-width:]
    low = min(recent)
    high = max(recent)
    span = high - low or 1.0
    result = "".join(
        SPARKLINE_CHARS[min(7, int(((v - low) / span) * 7))]
        for v in recent
    ).rjust(width)
    return Text(result)


# ── Bar widgets ───────────────────────────────────────────────────────

def _make_bar(
    ratio: float,
    width: int,
    style: str = HEALTHY,
    suffix: str = "",
) -> Text:
    """Build a ``\u2588\u2588\u2591\u2591`` bar with optional suffix."""
    filled = int(ratio * width)
    empty = width - filled
    bar = BAR_FILL * filled + BAR_EMPTY * empty
    return Text.assemble(bar, suffix, style=style)


def temp_bar(temp: Optional[float], max_temp: float = 100, width: int = 14) -> Text:
    """Temperature bar with severity colour."""
    if temp is None:
        return Text(BAR_EMPTY * width + "  ---", style=DIM)
    ratio = min(1.0, temp / max_temp)
    style = TEMP_SEVERITY(temp)
    return _make_bar(ratio, width, style, f"  {temp:.0f}\u00b0C")


def power_bar(value: Optional[float], limit: Optional[float], width: int = 12) -> Text:
    if value is None or limit is None or limit <= 0:
        return Text(BAR_EMPTY * width + "  ---", style=DIM)
    ratio = min(1.0, value / limit)
    style = RATIO_SEVERITY(ratio)
    return _make_bar(ratio, width, style, f"  {value:.0f}/{limit:.0f}W")


def vram_bar(used_mb: Optional[int], total_mb: Optional[int], width: int = 10) -> Text:
    if used_mb is None or total_mb is None or total_mb <= 0:
        return Text(BAR_EMPTY * width + "  ---", style=DIM)
    ratio = min(1.0, used_mb / total_mb)
    style = RATIO_SEVERITY(ratio)
    used_gb = used_mb / 1024
    total_gb = total_mb / 1024
    return _make_bar(ratio, width, style, f"  {used_gb:.1f}/{total_gb:.1f}GB")


def battery_bar(percent: Optional[int], width: int = 12) -> Text:
    if percent is None:
        return Text(BAR_EMPTY * width + "  ---", style=DIM)
    ratio = percent / 100.0
    style = BATTERY_SEVERITY(percent)
    return _make_bar(ratio, width, style, f"  {percent}%")


def fan_bar(rpm: Optional[int], max_rpm: int = 6000, width: int = 12) -> Text:
    if rpm is None:
        return Text(BAR_EMPTY * width + "  ---", style=DIM)
    ratio = min(1.0, rpm / max_rpm)
    style = RATIO_SEVERITY(ratio)
    return _make_bar(ratio, width, style, f"  {rpm}")


def progress_bar(current: Optional[float], maximum: Optional[float], width: int = 16) -> Text:
    if current is None or maximum is None or maximum <= 0:
        return Text(BAR_EMPTY * width + "  ---", style=DIM)
    ratio = min(1.0, current / maximum)
    style = RATIO_SEVERITY(ratio)
    pct = int(ratio * 100)
    return _make_bar(ratio, width, style, f"  {pct}%")


def mini_temp_bar(temp: Optional[float], max_temp: float = 100, width: int = 8) -> Text:
    """Compact temperature bar."""
    if temp is None:
        return Text(BAR_EMPTY * width + " ---", style=DIM)
    ratio = min(1.0, temp / max_temp)
    style = TEMP_SEVERITY(temp)
    return _make_bar(ratio, width, style, f" {temp:.0f}\u00b0C")


def mini_power_bar(value: Optional[float], limit: Optional[float], width: int = 8) -> Text:
    if value is None or limit is None or limit <= 0:
        return Text(BAR_EMPTY * width + " ---", style=DIM)
    ratio = min(1.0, value / limit)
    style = RATIO_SEVERITY(ratio)
    return _make_bar(ratio, width, style, f" {value:.0f}/{limit:.0f}W")


def mini_battery_bar(percent: Optional[int], width: int = 8) -> Text:
    if percent is None:
        return Text(BAR_EMPTY * width + " ---", style=DIM)
    ratio = percent / 100.0
    style = BATTERY_SEVERITY(percent)
    return _make_bar(ratio, width, style, f" {percent}%")


# ── Power limit string helper ─────────────────────────────────────────

def limit_str(value: Optional[float], limit: Optional[float], unit: str = "W") -> str:
    """``value / limit`` string for power/thermal limits."""
    if value is None and limit is None:
        return "---"
    if unit == "C":
        left = f"{value:.1f}\u00b0C" if value is not None else "---"
        right = f"{limit:.0f}\u00b0C" if limit is not None else "---"
    else:
        left = f"{value:.1f} {unit}" if value is not None else "---"
        right = f"{limit:.1f} {unit}" if limit is not None else "---"
    return f"{left} / {right}"
