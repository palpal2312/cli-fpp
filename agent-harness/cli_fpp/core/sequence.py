"""Sequence transport — mirrors index.php pause/step controls."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def toggle_pause(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/sequence/current/togglePause", base_url=base_url)


def step(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/sequence/current/step", base_url=base_url)


def stop(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/sequence/current/stop", base_url=base_url)
