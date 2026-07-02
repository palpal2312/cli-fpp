#!/usr/bin/env python3
"""Generate cli_fpp/cli-manifest.json from Click command tree."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))


def walk_commands(group: click.Group, prefix: str = "") -> dict:
    entries: dict = {}
    for name, cmd in sorted(group.commands.items(), key=lambda x: x[0]):
        path = f"{prefix} {name}".strip()
        key = path.replace(" ", ".")
        if isinstance(cmd, click.Group):
            entries[key] = {
                "name": name,
                "path": path,
                "type": "group",
                "description": (cmd.help or "").strip(),
                "subcommands": sorted(cmd.commands.keys()),
            }
            entries.update(walk_commands(cmd, path))
        else:
            entries[key] = {
                "name": name,
                "path": path,
                "type": "command",
                "description": (cmd.help or "").strip(),
            }
    return entries


def main() -> int:
    from cli_fpp import __version__
    from cli_fpp.cli import cli  # noqa: WPS433 — registers full command tree

    manifest = {
        "version": __version__,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "entry": "cli-fpp",
        "packaging": {
            "style": "claudekit-like",
            "entryModule": "cli_fpp.__main__:main",
            "thinBin": "bin/cli-fpp",
        },
        "runtime": {
            "python": ">=3.10",
            "gh": ">=2.20.0 (system; optional except contribute --github)",
        },
        "commands": walk_commands(cli),
    }
    out = HARNESS / "cli_fpp" / "cli-manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(manifest['commands'])} commands)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
