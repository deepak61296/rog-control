from __future__ import annotations

from src.core.sensors import parse_meminfo, parse_proc_stat, utilization_percent

PROC_STAT = """\
cpu  100 0 100 700 100 0 0 0 0 0
cpu0 50 0 50 350 50 0 0 0 0 0
cpu1 50 0 50 350 50 0 0 0 0 0
intr 12345
ctxt 6789
"""

PROC_STAT_LATER = """\
cpu  200 0 200 750 150 0 0 0 0 0
cpu0 150 0 150 350 50 0 0 0 0 0
cpu1 50 0 50 400 100 0 0 0 0 0
intr 12345
ctxt 6789
"""

MEMINFO = """\
MemTotal:       32049652 kB
MemFree:        11835976 kB
MemAvailable:   20308292 kB
Buffers:         1024000 kB
SwapTotal:       8388604 kB
SwapFree:        8388604 kB
"""


def test_parse_proc_stat_extracts_aggregate_and_cores() -> None:
    stats = parse_proc_stat(PROC_STAT)
    assert stats["cpu"] == (800, 1000)
    assert stats["cpu0"] == (400, 500)
    assert stats["cpu1"] == (400, 500)
    assert "intr" not in stats


def test_utilization_percent_between_samples() -> None:
    first = parse_proc_stat(PROC_STAT)
    second = parse_proc_stat(PROC_STAT_LATER)

    total = utilization_percent(second["cpu"], first["cpu"])
    assert total is not None and abs(total - 66.666) < 0.1

    busy_core = utilization_percent(second["cpu0"], first["cpu0"])
    assert busy_core == 100.0

    idle_core = utilization_percent(second["cpu1"], first["cpu1"])
    assert idle_core == 0.0


def test_utilization_percent_handles_zero_and_negative_delta() -> None:
    assert utilization_percent((100, 200), (100, 200)) is None
    assert utilization_percent((90, 190), (100, 200)) is None


def test_parse_meminfo_reports_used_and_swap() -> None:
    memory = parse_meminfo(MEMINFO)
    assert memory.total_mb == 32049652 // 1024
    assert memory.available_mb == 20308292 // 1024
    assert memory.used_mb == (32049652 - 20308292) // 1024
    assert memory.swap_total_mb == 8388604 // 1024
    assert memory.swap_used_mb == 0


def test_parse_meminfo_missing_fields() -> None:
    memory = parse_meminfo("Garbage: nonsense\n")
    assert memory.total_mb is None
    assert memory.used_mb is None
    assert memory.swap_total_mb is None
