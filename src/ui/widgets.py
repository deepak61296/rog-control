"""Custom monitoring widgets: nvtop-style braille graphs and gauge bars."""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

# Braille dot bits by (sub-row from top, sub-column): U+2800 + bits.
_DOT_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))

GraphSeries = tuple[list[float], str]  # (samples, rich color)


def build_braille_graph(
    series: list[GraphSeries],
    width: int,
    height: int,
    max_value: float = 100.0,
) -> list[Text]:
    """Render series into `height` rows of braille line-graph text.

    Each character cell packs 2 samples horizontally and 4 levels vertically,
    latest sample anchored to the right edge, like nvtop's charts. Vertical
    gaps between consecutive samples are filled so each series reads as a
    continuous line.
    """
    width = max(width, 1)
    height = max(height, 1)
    px_w = width * 2
    px_h = height * 4
    # cells[row][col] maps series index -> braille dot bits owned by it
    cells: list[list[dict[int, int] | None]] = [[None] * width for _ in range(height)]

    for index, (data, _color) in enumerate(series):
        points = data[-px_w:]
        offset = px_w - len(points)
        prev_y: int | None = None
        for sample, value in enumerate(points):
            x = offset + sample
            fraction = max(0.0, min(1.0, value / max_value)) if max_value > 0 else 0.0
            y = round(fraction * (px_h - 1))
            low, high = (y, y) if prev_y is None else (min(prev_y, y), max(prev_y, y))
            for yy in range(low, high + 1):
                row = height - 1 - (yy // 4)
                bit = _DOT_BITS[3 - (yy % 4)][x % 2]
                cell = cells[row][x // 2]
                if cell is None:
                    cell = cells[row][x // 2] = {}
                cell[index] = cell.get(index, 0) | bit
            prev_y = y

    lines: list[Text] = []
    for row in range(height):
        text = Text(no_wrap=True)
        for col in range(width):
            cell = cells[row][col]
            if not cell:
                text.append(" ")
                continue
            bits = 0
            for series_bits in cell.values():
                bits |= series_bits
            # Whichever series owns more dots in this cell colors it; ties go
            # to the earlier series so the primary line stays visually on top.
            winner = max(cell.items(), key=lambda item: (bin(item[1]).count("1"), -item[0]))[0]
            text.append(chr(0x2800 + bits), style=series[winner][1])
        lines.append(text)
    return lines


class BrailleGraph(Widget):
    """nvtop-style scrolling multi-series graph with a y-axis gutter."""

    DEFAULT_CSS = """
    BrailleGraph {
        height: 1fr;
        width: 1fr;
    }
    """

    GUTTER = 4

    def __init__(self, max_value: float = 100.0, axis_style: str = "#3d4450", **kwargs) -> None:
        super().__init__(**kwargs)
        self.max_value = max_value
        self.axis_style = axis_style
        self._series: list[GraphSeries] = []

    def set_series(self, series: list[GraphSeries]) -> None:
        self._series = series
        self.refresh()

    def render(self) -> Text:
        width = self.size.width
        height = self.size.height
        if width <= self.GUTTER or height < 1:
            return Text("")

        rows = build_braille_graph(self._series, width - self.GUTTER, height, self.max_value)
        mid = height // 2
        output = Text(no_wrap=True)
        for row, line in enumerate(rows):
            if row == 0:
                label = f"{self.max_value:>3.0f}┤"
            elif row == height - 1:
                label = "  0┤"
            elif row == mid and height > 2:
                label = f"{self.max_value / 2:>3.0f}┤"
            else:
                label = "   │"
            output.append(label, style=self.axis_style)
            output.append(line)
            if row < height - 1:
                output.append("\n")
        return output


class GaugeBar(Widget):
    """Single-line labelled meter: LABEL ▕████░░░░▏ value-text."""

    DEFAULT_CSS = """
    GaugeBar {
        height: 1;
        width: 1fr;
    }
    """

    def __init__(
        self,
        label: str,
        label_width: int = 6,
        high_is_good: bool = False,
        label_style: str = "#8b949e",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.label_width = label_width
        self.high_is_good = high_is_good
        self.label_style = label_style
        self._fraction: float | None = None
        self._text = "---"

    def set_gauge(self, value: float | None, maximum: float | None, text: str) -> None:
        if value is None or maximum is None or maximum <= 0:
            self._fraction = None
        else:
            self._fraction = max(0.0, min(1.0, value / maximum))
        self._text = text
        self.refresh()

    def _bar_color(self) -> str:
        fraction = self._fraction or 0.0
        if self.high_is_good:
            fraction = 1.0 - fraction
        if fraction < 0.60:
            return "#39ff14"
        if fraction < 0.85:
            return "#ffb700"
        return "#ff0033"

    def render(self) -> Text:
        width = self.size.width
        text_width = len(self._text)
        bar_width = width - self.label_width - text_width - 4
        output = Text(no_wrap=True)
        output.append(f"{self.label:<{self.label_width}}", style=self.label_style)
        if bar_width >= 4 and self._fraction is not None:
            filled = round(self._fraction * bar_width)
            color = self._bar_color()
            output.append("▕", style=self.axis_color())
            output.append("█" * filled, style=color)
            output.append("░" * (bar_width - filled), style="#22272e")
            output.append("▏ ", style=self.axis_color())
        elif bar_width >= 4:
            output.append("▕", style=self.axis_color())
            output.append("░" * bar_width, style="#22272e")
            output.append("▏ ", style=self.axis_color())
        output.append(self._text, style="bold")
        return output

    @staticmethod
    def axis_color() -> str:
        return "#3d4450"


def build_core_strip(
    utils: list[float] | None,
    freqs_mhz: list[int] | None,
    group: int = 4,
) -> Text:
    """One-line per-core load meter using block glyphs, colored by load."""
    blocks = "▁▂▃▄▅▆▇█"
    text = Text(no_wrap=True)
    text.append("CORES ", style="#8b949e")
    if not utils:
        text.append("---", style="#8b949e")
        return text

    for index, util in enumerate(utils):
        if index and index % group == 0:
            text.append(" ")
        level = min(len(blocks) - 1, int(util / 100.0 * (len(blocks) - 1) + 0.5))
        if util >= 85.0:
            color = "#ff0033"
        elif util >= 60.0:
            color = "#ffb700"
        else:
            color = "#39ff14"
        text.append(blocks[level], style=color)

    if freqs_mhz:
        avg_ghz = sum(freqs_mhz) / len(freqs_mhz) / 1000.0
        peak_ghz = max(freqs_mhz) / 1000.0
        text.append(f"  AVG {avg_ghz:.2f}  PEAK {peak_ghz:.2f} GHz", style="#8b949e")
    return text
