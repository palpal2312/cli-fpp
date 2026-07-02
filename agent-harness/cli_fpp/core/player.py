"""Player status — mirrors index.php status widgets."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def status(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/player/status", base_url=base_url)


def current(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/player/current", base_url=base_url)
