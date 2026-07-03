"""Call cli_fpp.core.agent_tools directly from Python.

Prereqs:
    pip install -e agent-harness/.[dev]
    cli-fpp target add shop-a --fpp-url http://192.168.1.10:81 --fpp-user admin --fpp-password <secret>
"""

from __future__ import annotations

import json

from cli_fpp.core import agent_tools


def dump(label: str, value: object) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def main() -> None:
    dump("targets", agent_tools.list_targets())
    dump("suggest", agent_tools.suggest("chạy playlist Holiday"))
    dump("guide:playlist", agent_tools.get_guide("playlist"))
    dump("tool_schema", agent_tools.tool_schema())

    dispatched = agent_tools.dispatch_tool(
        "cli_fpp_suggest",
        {"prompt": "play playlist Holiday"},
    )
    dump("dispatch:cli_fpp_suggest", dispatched)


if __name__ == "__main__":
    main()
