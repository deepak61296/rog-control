from __future__ import annotations

import sys

from src.core.process import run_command


def test_run_command_returns_stdout_for_success() -> None:
    success, output = run_command([sys.executable, "-c", "print('ok')"], timeout=5)

    assert success
    assert output.strip() == "ok"


def test_run_command_reports_timeout() -> None:
    success, output = run_command(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        timeout=1,
    )

    assert not success
    assert "timed out after 1s" in output
