"""System and fppd management."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def status(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/system/status", base_url=base_url)


def info(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/system/info", base_url=base_url)


def fppd_status(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/fppd/status", base_url=base_url)


def fppd_version(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/fppd/version", base_url=base_url)


def fppd_restart(*, quick: bool = True, base_url: str | None = None) -> Any:
    params = {"quick": "true"} if quick else None
    return api.api_get("/api/system/fppd/restart", base_url=base_url, params=params)


def reboot(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/system/reboot", base_url=base_url)


def shutdown(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/system/shutdown", base_url=base_url)
