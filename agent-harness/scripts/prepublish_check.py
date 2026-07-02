#!/usr/bin/env python3
"""Pre-publish checks (ClaudeKit verify:package style)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
PKG = HARNESS / "cli_fpp"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit_code = 1


def main() -> int:
    errors: list[str] = []
    from cli_fpp import __version__

    manifest_path = PKG / "cli-manifest.json"
    if not manifest_path.exists():
        errors.append("cli-manifest.json missing — run: python scripts/generate_cli_manifest.py")
    else:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("version") != __version__:
            errors.append(f"manifest version {data.get('version')} != __version__ {__version__}")

    for rel in (
        "skills/experiences_bundled.json",
        "skills/SKILL.md",
        "skills/contributions/README.md",
        "__main__.py",
    ):
        if not (PKG / rel).exists():
            errors.append(f"missing package file: cli_fpp/{rel}")

    thin_bin = HARNESS / "bin" / "cli-fpp"
    if not thin_bin.exists():
        errors.append("missing bin/cli-fpp thin entry")

    if errors:
        for err in errors:
            fail(err)
        return 1

    print("prepublish-check OK")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(HARNESS))
    raise SystemExit(main())
