"""Run the same cli-fpp workflow on multiple target profiles."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def run_cli(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        ["cli-fpp", "--json", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def main() -> None:
    playlist = sys.argv[1] if len(sys.argv) > 1 else "Holiday"
    targets = sys.argv[2:] or ["shop-a", "shop-b"]

    for target in targets:
        print(f"== Target: {target} ==")
        dump_ping = run_cli(["-t", target, "ping"])
        dump_status = run_cli(["-t", target, "player", "status"])
        dump_play = run_cli(["--yes", "-t", target, "playlist", "play", playlist, "--repeat"])
        dump_current = run_cli(["-t", target, "player", "current"])

        print(json.dumps({"ping": dump_ping}, indent=2, ensure_ascii=False))
        print(json.dumps({"status": dump_status}, indent=2, ensure_ascii=False))
        print(json.dumps({"play": dump_play}, indent=2, ensure_ascii=False))
        print(json.dumps({"current": dump_current}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
