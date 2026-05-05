#!/usr/bin/env python3
"""ROG Control entrypoint."""

from __future__ import annotations

import argparse
import sys

from src.ui.app import RogControlApp


def main() -> int:
    parser = argparse.ArgumentParser(description="ROG Control terminal dashboard")
    parser.parse_args()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("ROG Control requires an interactive terminal.")
        return 1

    app = RogControlApp()
    return app.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
