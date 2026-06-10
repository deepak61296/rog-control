"""Menu rendering for ROG Control."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

MENU_COLORS = {
    "cpu": "cyan",
    "power": "magenta",
    "fan_profile": "blue",
    "fan_curve": "blue",
    "quick": "bright_green",
    "help": "yellow",
}

MENU_TITLES = {
    "cpu": "CPU Limit Presets",
    "power": "Power Presets",
    "fan_profile": "Fan Profiles",
    "fan_curve": "Fan Curve Presets",
    "quick": "Quick Presets",
    "help": "Help",
}


def render_menu(
    active_menu: str,
    cpu_presets: dict,
    power_presets: dict,
    fan_profiles: dict,
    fan_curves: dict,
    quick_presets: dict,
    power_controller=None,
) -> Panel:
    renderers = {
        "cpu": lambda: _cpu_menu_panel(cpu_presets),
        "power": lambda: _power_menu_panel(power_presets, power_controller),
        "fan_profile": lambda: _fan_profile_menu_panel(fan_profiles),
        "fan_curve": lambda: _fan_curve_menu_panel(fan_curves),
        "quick": lambda: _quick_menu_panel(quick_presets),
        "help": _help_menu_panel,
    }
    renderer = renderers.get(active_menu)
    if renderer is None:
        return _help_menu_panel()
    return renderer()


def _cpu_menu_panel(presets: dict) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    table.add_column()
    for key, (label, freq) in presets.items():
        table.add_row(f"[bold]{key}[/]", f"{label} ({freq / 1_000_000:.2f} GHz)")
    table.add_row("[bold]b[/]", "Back")
    return Panel(table, title="CPU Limit Presets", border_style="cyan")


def _power_menu_panel(presets: dict, power_controller=None) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    table.add_column()
    for key, (label, preset_name) in presets.items():
        if power_controller and preset_name in power_controller.POWER_PRESETS:
            preset = power_controller.POWER_PRESETS[preset_name]
            table.add_row(f"[bold]{key}[/]", f"{label} ({preset['stapm'] // 1000}W STAPM)")
        else:
            table.add_row(f"[bold]{key}[/]", label)
    table.add_row("[bold]b[/]", "Back")
    return Panel(table, title="Power Presets", border_style="magenta")


def _fan_profile_menu_panel(presets: dict) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    table.add_column()
    for key, label in presets.items():
        table.add_row(f"[bold]{key}[/]", label)
    table.add_row("[bold]b[/]", "Back")
    return Panel(table, title="Fan Profiles", border_style="blue")


def _fan_curve_menu_panel(presets: dict) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    table.add_column()
    for key, name in presets.items():
        table.add_row(f"[bold]{key}[/]", name.replace("_", " ").title())
    table.add_row("[bold]d[/]", "Reset to firmware defaults")
    table.add_row("[bold]b[/]", "Back")
    return Panel(table, title="Fan Curve Presets", border_style="blue")


def _quick_menu_panel(presets: dict) -> Panel:
    table = Table.grid(expand=True)
    table.add_column()
    table.add_column()
    for key, preset in presets.items():
        table.add_row(f"[bold]{key}[/]", preset[0])
    table.add_row("[bold]b[/]", "Back")
    return Panel(table, title="Quick Presets", border_style="bright_green")


def _help_menu_panel() -> Panel:
    text = Text.from_markup(
        "This dashboard updates automatically.\n\n"
        "Use the numbered shortcuts to open a control menu.\n"
        "Unsupported backends stay visible but are marked unavailable.\n"
        "Press [bold]b[/], [bold]Esc[/], or [bold]q[/] to close a menu."
    )
    return Panel(text, title="Help", border_style="yellow")
