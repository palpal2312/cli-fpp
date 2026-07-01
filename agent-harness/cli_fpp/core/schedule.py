"""Schedule operations."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def list_schedules(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/schedule", base_url=base_url)


def reload(*, base_url: str | None = None) -> Any:
    return api.api_get(api.command_path("Reload Schedule"), base_url=base_url)
