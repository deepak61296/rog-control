"""Theme constants and severity helpers for rog-control.

Provides a single source of truth for colors, border styles, box types,
and threshold-based severity mappings used across all UI widgets.
"""

from __future__ import annotations

from typing import Optional

from rich import box


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

# ── Box types for different panel categories ─────────────────────────
BOX_HEADER = box.DOUBLE
BOX_DATA = box.ROUNDED
BOX_MENU = box.HEAVY
BOX_FOOTER = box.SQUARE

# ── Badge / dot colors ───────────────────────────────────────────────
DOT_OK = "green bold"
DOT_WARN = "yellow bold"
DOT_MISSING = "yellow"
DOT_ERROR = "red bold"

# ── Progress bar characters ──────────────────────────────────────────
BAR_FILL = "\u2588"
BAR_EMPTY = "\u2591"
SPARKLINE_CHARS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


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


def battery_border(percent: Optional[int]) -> str:
    """Return border colour for a battery percentage."""
    if percent is None:
        return BORDER_DIM
    if percent < 20:
        return BORDER_CRITICAL
    if percent < 50:
        return BORDER_WARN
    return BORDER_HEALTHY


# ── Gradient colour helper ───────────────────────────────────────────

def gradient_color(ratio: float) -> str:
    """Return a Rich colour string interpolated along a heat gradient.

    0.0   -> green
    0.33  -> yellow
    0.66  -> orange1
    1.0   -> red
    """
    ratio = max(0.0, min(1.0, ratio))
    if ratio < 0.33:
        t = ratio / 0.33
        return _blend_rich((0, 128, 0), (200, 200, 0), t)
    elif ratio < 0.66:
        t = (ratio - 0.33) / 0.33
        return _blend_rich((200, 200, 0), (255, 128, 0), t)
    else:
        t = (ratio - 0.66) / 0.34
        return _blend_rich((255, 128, 0), (220, 0, 0), t)


def _blend_rich(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    """Blend two RGB tuples and return a Rich-compatible colour string."""
    r = int(a[0] + (b[0] - a[0]) * t)
    g = int(a[1] + (b[1] - a[1]) * t)
    bl = int(a[2] + (b[2] - a[2]) * t)
    return f"rgb({r},{g},{bl})"
