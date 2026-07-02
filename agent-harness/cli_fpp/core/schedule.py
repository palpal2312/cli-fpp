"""Schedule operations."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def list_schedules(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/schedule", base_url=base_url)


def reload(*, base_url: str | None = None) -> Any:
    return api.api_post("/api/schedule/reload", None, base_url=base_url)


def extend(seconds: int, *, base_url: str | None = None) -> Any:
    return api.api_get(api.command_path("Extend Schedule", str(seconds)), base_url=base_url)


def start_next(*, base_url: str | None = None) -> Any:
    return api.api_get(api.command_path("Start Next Scheduled Item"), base_url=base_url)
