"""Custom Rich widgets for sci-fi themed ROG Control dashboard."""

from rich.panel import Panel
from rich.text import Text
from rich.bar import Bar
from rich.columns import Columns
from rich.table import Table
from rich.console import RenderableType, Group
from rich.align import Align
from typing import Optional, List, Tuple
import math

from src.ui.theme import (
    NEON_GREEN, BRIGHT_GREEN, TEAL, CYAN, WARNING_YELLOW, ERROR_RED, ORANGE,
    temp_style, usage_style, SPARKLINE_CHARS, get_gradient_color
)


def colored_bar(value: float, max_value: float, width: int = 20, label: str = "") -> Text:
    """Create a colored bar representation based on value percentage."""
    if max_value == 0:
        percent = 0
    else:
        percent = min(100, (value / max_value) * 100)

    filled = int((percent / 100) * width)
    empty = width - filled

    # Choose color based on percentage
    if percent >= 80:
        color = ERROR_RED
    elif percent >= 60:
        color = ORANGE
    elif percent >= 40:
        color = WARNING_YELLOW
    else:
        color = NEON_GREEN

    bar_text = Text()
    bar_text.append("█" * filled, style=color)
    bar_text.append("░" * empty, style="dim white")
    if label:
        bar_text.append(f" {value:.1f}/{max_value:.1f}", style="dim white")

    return bar_text


def temperature_gauge(temp_c: Optional[float], width: int = 20) -> Text:
    """Render temperature as a colored gauge."""
    if temp_c is None:
        return Text("---", style="dim white")

    # Temperature range: 30-100°C
    min_temp = 30
    max_temp = 100
    if temp_c < min_temp:
        temp_c = min_temp
    if temp_c > max_temp:
        temp_c = max_temp

    percent = ((temp_c - min_temp) / (max_temp - min_temp)) * 100
    filled = int((percent / 100) * width)
    empty = width - filled

    style = temp_style(temp_c)

    gauge = Text()
    gauge.append("█" * filled, style=style)
    gauge.append("░" * empty, style="dim white")
    gauge.append(f" {temp_c:.1f}°C", style=style)

    return gauge


def power_gauge(power_w: Optional[float], limit_w: Optional[float] = None, width: int = 20) -> Text:
    """Render power consumption as a colored gauge."""
    if power_w is None:
        return Text("---", style="dim white")

    if limit_w is None:
        limit_w = 100.0  # Default max

    percent = min(100, (power_w / limit_w) * 100)
    filled = int((percent / 100) * width)
    empty = width - filled

    if percent >= 90:
        color = ERROR_RED
    elif percent >= 75:
        color = WARNING_YELLOW
    elif percent >= 50:
        color = ORANGE
    else:
        color = NEON_GREEN

    gauge = Text()
    gauge.append("█" * filled, style=color)
    gauge.append("░" * empty, style="dim white")
    gauge.append(f" {power_w:.1f}W", style=color)

    return gauge


def rpm_gauge(rpm: Optional[int], width: int = 15) -> Text:
    """Render fan RPM as a gauge."""
    if rpm is None:
        return Text("---", style="dim white")

    # Typical fan range: 0-6000 RPM
    max_rpm = 6000
    if rpm > max_rpm:
        rpm = max_rpm

    percent = (rpm / max_rpm) * 100
    filled = int((percent / 100) * width)
    empty = width - filled

    if rpm >= 4500:
        color = ERROR_RED
    elif rpm >= 3000:
        color = WARNING_YELLOW
    else:
        color = CYAN

    gauge = Text()
    gauge.append("█" * filled, style=color)
    gauge.append("░" * empty, style="dim white")
    gauge.append(f" {rpm} RPM", style=color)

    return gauge


def enhanced_sparkline(values: List[float], width: int = 20, height: int = 1) -> Text:
    """Create an enhanced sparkline with gradient colors."""
    if len(values) < 2:
        return Text(" " * width, style="dim white")

    # Get recent values up to width
    recent = values[-width:]
    low = min(recent)
    high = max(recent)
    span = high - low or 1.0

    result = Text()
    for value in recent:
        ratio = (value - low) / span
        idx = min(len(SPARKLINE_CHARS) - 1, int(ratio * len(SPARKLINE_CHARS)))
        color = get_gradient_color(ratio)
        result.append(SPARKLINE_CHARS[idx], style=color)

    return result


def metric_panel(title: str, metrics: List[Tuple[str, RenderableType]], border_style: str = NEON_GREEN) -> Panel:
    """Create a panel with labeled metrics."""
    table = Table.grid(expand=True)
    table.add_column(style="bold white", ratio=1)
    table.add_column(justify="right", ratio=1)

    for label, value in metrics:
        if isinstance(value, str):
            table.add_row(label, Text(value, style="bold"))
        else:
            table.add_row(label, value)

    return Panel(
        table,
        title=f"[bold]{title}[/bold]",
        border_style=border_style,
        padding=(0, 1),
    )


def status_badge(label: str, active: bool, color_active: str = NEON_GREEN, color_inactive: str = "dim white") -> Text:
    """Create a status badge with dot indicator."""
    dot = "●" if active else "○"
    color = color_active if active else color_inactive
    return Text(f"{dot} {label}", style=color)


def header_panel(title: str, subtitle: str = "", badges: List[RenderableType] = None) -> Panel:
    """Create a sci-fi styled header panel."""
    from src.ui.theme import SCI_FI_DOUBLE

    elements = []
    if title:
        elements.append(Align.center(Text(title, style=f"bold {NEON_GREEN}", justify="center")))
    if subtitle:
        elements.append(Align.center(Text(subtitle, style=f"dim {TEAL}", justify="center")))
    if badges:
        elements.append(Columns(badges, align="center", expand=True))

    return Panel(
        Group(*elements) if len(elements) > 1 else elements[0],
        border_style=NEON_GREEN,
        box=SCI_FI_DOUBLE,
        padding=(1, 2),
    )


def footer_panel(help_text: str, status_text: str = "", status_style: str = NEON_GREEN) -> Panel:
    """Create a footer panel with help and status."""
    from src.ui.theme import SCI_FI_BOX

    elements = [Text.from_markup(help_text)]
    if status_text:
        elements.append(Text(status_text, style=status_style))

    return Panel(
        Group(*elements),
        border_style=NEON_GREEN,
        box=SCI_FI_BOX,
        padding=(0, 1),
    )


def progress_bar_horizontal(value: float, max_value: float, width: int = 30,
                            label: str = "", show_percent: bool = True) -> Text:
    """Create a horizontal progress bar."""
    if max_value == 0:
        percent = 0
    else:
        percent = min(100, (value / max_value) * 100)

    filled = int((percent / 100) * width)
    empty = width - filled

    style = usage_style(percent)

    bar = Text()
    bar.append("━" * filled, style=style)
    bar.append("─" * empty, style="dim white")
    if show_percent:
        bar.append(f" {percent:.0f}%", style=style)
    if label:
        bar = Text(label + ": ", style="bold white") + bar

    return bar