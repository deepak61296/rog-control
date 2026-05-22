"""Theme constants and severity helpers for rog-control.

Provides a single source of truth for colors, border styles,
and threshold-based severity mappings used across all UI widgets.
"""

from __future__ import annotations

from typing import Optional


# ── General palette ──────────────────────────────────────────────────
HEALTHY = "green"
WARN = "yellow"
HOT = "bold orange1"
CRITICAL = "bold red"
DIM = "dim"
ACTIVE = "bold cyan"
TITLE = "bold green"
NORMAL = ""
DISABLED = "bold yellow"

# ── Border styles by severity ────────────────────────────────────────
BORDER_HEALTHY = "green"
BORDER_WARN = "yellow"
BORDER_HOT = "orange1"
BORDER_CRITICAL = "red"
BORDER_ACTIVE = "cyan"
BORDER_DIM = "grey50"

# ── Badge / dot colors ───────────────────────────────────────────────
DOT_OK = "green bold"
DOT_WARN = "yellow bold"
DOT_MISSING = "yellow"
DOT_ERROR = "red bold"

# ── Progress bar characters ──────────────────────────────────────────
BAR_FILL = "█"
BAR_EMPTY = "░"
SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


# ── Severity helpers ──────────────────────────────────────────────────

def temp_severity(temp_c: Optional[float]) -> str:
    """Return style for a temperature value."""
    if temp_c is None:
        return DIM
    if temp_c >= 90:
        return CRITICAL
    if temp_c >= 85:
        return HOT
    if temp_c >= 70:
        return WARN
    return HEALTHY


def temp_border(temp_c: Optional[float]) -> str:
    """Return border colour for a temperature value."""
    if temp_c is None:
        return BORDER_DIM
    if temp_c >= 90:
        return BORDER_CRITICAL
    if temp_c >= 85:
        return BORDER_HOT
    if temp_c >= 70:
        return BORDER_WARN
    return BORDER_HEALTHY


def ratio_severity(ratio: float) -> str:
    """Return style for a 0..1 utilisation / power ratio."""
    if ratio >= 0.95:
        return CRITICAL
    if ratio >= 0.85:
        return HOT
    if ratio >= 0.70:
        return WARN
    return HEALTHY


def ratio_border(ratio: float) -> str:
    """Return border colour for a 0..1 utilisation / power ratio."""
    if ratio >= 0.95:
        return BORDER_CRITICAL
    if ratio >= 0.85:
        return BORDER_HOT
    if ratio >= 0.70:
        return BORDER_WARN
    return BORDER_HEALTHY


def util_severity(percent: Optional[int]) -> str:
    """Return style for a utilisation percentage."""
    if percent is None:
        return DIM
    if percent >= 90:
        return CRITICAL
    if percent >= 70:
        return WARN
    return HEALTHY


def battery_severity(percent: Optional[int]) -> str:
    """Return style for a battery percentage."""
    if percent is None:
        return DIM
    if percent < 20:
        return CRITICAL
    if percent < 50:
        return WARN
    return HEALTHY
