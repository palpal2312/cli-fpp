"""GPIO — mirrors gpio.php config; runtime pin control via REST."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def list_pins(*, names_only: bool = False, base_url: str | None = None) -> Any:
    params = {"list": "true"} if names_only else None
    return api.api_get("/api/gpio", base_url=base_url, params=params)


def get_pin(pin: str, *, base_url: str | None = None) -> Any:
    from urllib.parse import quote

    return api.api_get(f"/api/gpio/{quote(pin, safe='')}", base_url=base_url)


def set_pin(pin: str, value: int, *, base_url: str | None = None) -> Any:
    from urllib.parse import quote

    return api.api_post(f"/api/gpio/{quote(pin, safe='')}", {"value": value}, base_url=base_url)
