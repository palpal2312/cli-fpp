"""Thin entrypoint — packaged CLI (ClaudeKit-style bin → module)."""

from __future__ import annotations

import sys

_MIN_PYTHON = (3, 10)


def _check_python() -> None:
    if sys.version_info < _MIN_PYTHON:
        major, minor = _MIN_PYTHON
        sys.stderr.write(
            f"Python {major}.{minor}+ is required. Current: "
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
        )
        sys.exit(1)


def main() -> None:
    _check_python()
    from cli_fpp.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
