from __future__ import annotations

from src.core.power import PowerController
from src.ui.widgets import build_braille_graph, build_core_strip


def test_braille_graph_dimensions_and_anchoring() -> None:
    data = [0.0, 50.0, 100.0]
    rows = build_braille_graph([(data, "green")], width=10, height=4)

    assert len(rows) == 4
    assert all(len(row.plain) == 10 for row in rows)
    # Latest (100%) sample must reach the top row at the right edge.
    assert rows[0].plain[-2:].strip() != ""
    # Nothing plotted at the far left: only 3 samples for 20 pixel columns.
    assert rows[-1].plain[0] == " "


def test_braille_graph_empty_and_clamped_input() -> None:
    rows = build_braille_graph([], width=8, height=3)
    assert [row.plain for row in rows] == [" " * 8] * 3

    # Out-of-range values must clamp, not crash or escape the grid.
    rows = build_braille_graph([([-50.0, 500.0], "red")], width=4, height=2)
    assert len(rows) == 2
    assert all(len(row.plain) == 4 for row in rows)


def test_braille_graph_two_series_render_distinct_colors() -> None:
    high = [90.0] * 20
    low = [10.0] * 20
    rows = build_braille_graph([(high, "#39ff14"), (low, "#00e5ff")], width=10, height=4)
    styles = {str(span.style) for row in rows for span in row.spans}
    assert "#39ff14" in styles
    assert "#00e5ff" in styles


def test_core_strip_levels_and_missing_data() -> None:
    strip = build_core_strip([0.0, 50.0, 100.0], [1400, 2800, 4200])
    assert "▁" in strip.plain
    assert "█" in strip.plain
    assert "AVG 2.80" in strip.plain
    assert "PEAK 4.20" in strip.plain

    empty = build_core_strip(None, None)
    assert "---" in empty.plain


def test_power_apply_custom_clamps_both_directions(monkeypatch) -> None:
    controller = PowerController.__new__(PowerController)
    captured: list[list[str]] = []

    def fake_run(args: list[str]) -> tuple[bool, str]:
        captured.append(args)
        return True, "ok"

    controller._run_ryzenadj = fake_run  # type: ignore[method-assign]

    controller.apply_custom(stapm=0, fast=999999, slow=-5, tctl=200)
    assert captured == [
        [
            "--stapm-limit=5000",
            "--fast-limit=80000",
            "--slow-limit=5000",
            "--tctl-temp=95",
        ]
    ]

    captured.clear()
    # slow must never sit below stapm, fast never below slow.
    controller.apply_custom(stapm=45000, fast=10000, slow=20000, tctl=10)
    assert captured == [
        [
            "--stapm-limit=45000",
            "--fast-limit=45000",
            "--slow-limit=45000",
            "--tctl-temp=60",
        ]
    ]
