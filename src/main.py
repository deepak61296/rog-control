#!/usr/bin/env python3
"""ROG Control entrypoint."""

from __future__ import annotations

import argparse
import sys

from src.ui.app import RogControlApp
from src.config import Config


def main() -> int:
    parser = argparse.ArgumentParser(description="ROG Control terminal dashboard")
    parser.add_argument("--config", type=str, help="Path to config file")
    args = parser.parse_args()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("ROG Control requires an interactive terminal.")
        return 1

    # Load configuration
    config = Config()
    if args.config:
        config.CONFIG_FILE = args.config
        config.load()

    app = RogControlApp(config)
    return app.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
