"""Sci-fi green theme for ROG Control - btop-inspired."""

from rich.style import Style
from rich.theme import Theme
from rich.box import DOUBLE, HEAVY, ROUNDED, SIMPLE

# Primary sci-fi green palette (btop-inspired)
NEON_GREEN = "#00ff00"
BRIGHT_GREEN = "#00ff88"
TEAL = "#00cc88"
CYAN = "#00ffff"
DIM_GREEN = "#008844"

# Cyberpunk accent colors
HOT_PINK = "#ff00ff"
ELECTRIC_BLUE = "#00aaff"
VIOLET = "#aa00ff"
NEON_ORANGE = "#ff6600"

# Warning/Error colors
WARNING_YELLOW = "#ffff00"
ERROR_RED = "#ff4444"
ORANGE = "#ff8800"

# UI element colors
BORDER_GREEN = "#00aa44"
HEADER_BG = "#002211"
PANEL_BG = "#001108"

# Glow effects (using bold + bright colors)
GLOW_GREEN = Style(color=NEON_GREEN, bold=True)
GLOW_CYAN = Style(color=CYAN, bold=True)
GLOW_PINK = Style(color=HOT_PINK, bold=True)

# Text styles
TEXT_PRIMARY = Style(color=NEON_GREEN, bold=True)
TEXT_SECONDARY = Style(color=TEAL)
TEXT_DIM = Style(color=DIM_GREEN)
TEXT_BRIGHT = Style(color=BRIGHT_GREEN, bold=True)

# Value styles based on state
VALUE_NORMAL = Style(color=NEON_GREEN)
VALUE_WARNING = Style(color=WARNING_YELLOW)
VALUE_CRITICAL = Style(color=ERROR_RED)
VALUE_INFO = Style(color=CYAN)

# Temperature color function
def temp_style(temp_c: float) -> Style:
    """Return appropriate style based on temperature."""
    if temp_c is None:
        return VALUE_INFO
    if temp_c >= 90:
        return VALUE_CRITICAL
    if temp_c >= 80:
        return Style(color=ORANGE)
    if temp_c >= 70:
        return VALUE_WARNING
    return VALUE_NORMAL

# Power/usage color function
def usage_style(percent: float) -> Style:
    """Return appropriate style based on usage percentage."""
    if percent is None:
        return VALUE_INFO
    if percent >= 90:
        return VALUE_CRITICAL
    if percent >= 75:
        return VALUE_WARNING
    return VALUE_NORMAL

# Border styles
BORDER_NORMAL = Style(color=BORDER_GREEN)
BORDER_ACTIVE = Style(color=NEON_GREEN, bold=True)
BORDER_WARNING = Style(color=WARNING_YELLOW)
BORDER_ERROR = Style(color=ERROR_RED)

# Use built-in Rich boxes for sci-fi look
SCI_FI_DOUBLE = DOUBLE
SCI_FI_HEAVY = HEAVY
SCI_FI_BOX = HEAVY  # Use HEAVY for compact view

# Rich Theme for easy console styling
ROG_THEME = Theme({
    "info": VALUE_INFO,
    "warning": VALUE_WARNING,
    "error": VALUE_CRITICAL,
    "primary": TEXT_PRIMARY,
    "secondary": TEXT_SECONDARY,
    "dim": TEXT_DIM,
    "bright": TEXT_BRIGHT,
    "temp.normal": VALUE_NORMAL,
    "temp.warning": VALUE_WARNING,
    "temp.critical": VALUE_CRITICAL,
    "usage.normal": VALUE_NORMAL,
    "usage.warning": VALUE_WARNING,
    "usage.critical": VALUE_CRITICAL,
})

# Sparkline characters with gradient (cyberpunk style)
SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"

# Gradient colors for sparklines (green to orange to red)
GRADIENT_COLORS = [
    "#00ff00",  # green - cool/low
    "#00ff44",
    "#00ff88",
    "#00ccff",  # cyan - mid
    "#00aaff",
    "#ffaa00",  # orange - warm
    "#ff6600",
    "#ff0000",  # red - hot
]

def get_gradient_color(ratio: float) -> str:
    """Return color based on value ratio (0-1)."""
    idx = int(ratio * (len(GRADIENT_COLORS) - 1))
    idx = min(idx, len(GRADIENT_COLORS) - 1)
    return GRADIENT_COLORS[idx]

def sparkline_color(value: float, min_val: float, max_val: float) -> str:
    """Return color style name based on value position in range."""
    if max_val == min_val:
        return "temp.normal"
    ratio = (value - min_val) / (max_val - min_val)
    if ratio >= 0.8:
        return "temp.critical"
    if ratio >= 0.6:
        return "temp.warning"
    return "temp.normal"