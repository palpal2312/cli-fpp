"""Effects — mirrors effects.php and status page effect widgets."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def list_effects(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/effects", base_url=base_url)


def running(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/fppd/effects", base_url=base_url)


def start(
    name: str,
    *,
    channel: int = 0,
    loop: bool = False,
    background: bool = False,
    fseq: bool = False,
    base_url: str | None = None,
) -> Any:
    loop_arg = "true" if loop else "false"
    bg_arg = "true" if background else "false"
    if fseq:
        return api.api_get(
            api.command_path("FSEQ Effect Start", name, loop_arg, bg_arg),
            base_url=base_url,
        )
    return api.api_get(
        api.command_path("Effect Start", name, str(channel), loop_arg, bg_arg),
        base_url=base_url,
    )


def stop(name: str | None = None, *, base_url: str | None = None) -> Any:
    if name:
        return api.api_post("/api/command", {"command": "Effect Stop", "args": [name]}, base_url=base_url)
    return api.api_post("/api/command", {"command": "Effect Stop", "args": []}, base_url=base_url)
