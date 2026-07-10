#!/usr/bin/env python3
"""ROG Control entrypoint."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import threading
from contextlib import AbstractContextManager

from src.ui.app import RogControlApp


class SudoSession(AbstractContextManager["SudoSession"]):
    """Prime and keep sudo credentials valid before the terminal UI starts."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.available = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "SudoSession":
        if not self.enabled or not shutil.which("sudo") or os.geteuid() == 0:
            return self

        cached = subprocess.run(
            ["sudo", "-n", "true"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if cached.returncode != 0:
            print("ROG Control needs sudo for CPU frequency and RyzenAdj controls.")
            try:
                prompted = subprocess.run(["sudo", "-v"], check=False)
            except KeyboardInterrupt:
                print("\nCancelled.")
                sys.exit(130)

            if prompted.returncode != 0:
                print("Continuing without sudo; write controls will be unavailable.", file=sys.stderr)
                return self

        self.available = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._keep_alive, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _keep_alive(self) -> None:
        while not self._stop_event.wait(60.0):
            subprocess.run(
                ["sudo", "-n", "-v"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="ROG Control terminal dashboard")
    parser.add_argument(
        "--no-sudo",
        action="store_true",
        help="skip the startup sudo prompt and run monitor-only if write access is unavailable",
    )
    args = parser.parse_args()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("ROG Control requires an interactive terminal.")
        return 1

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    with SudoSession(enabled=not args.no_sudo):
        app = RogControlApp()
        app.run()
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
