"""Pixel overlays — mirrors pixeloverlaymodels.php and WLED overlay UI."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def models(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/overlays/models", base_url=base_url)


def running(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/overlays/running", base_url=base_url)


def settings(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/overlays/settings", base_url=base_url)


def model_info(name: str, *, base_url: str | None = None) -> Any:
    from urllib.parse import quote

    return api.api_get(f"/api/overlays/model/{quote(name, safe='')}", base_url=base_url)


def stop_model_effects(model: str, *, base_url: str | None = None) -> Any:
    return api.api_get(
        api.command_path("Overlay Model Effect", model, "Enabled", "Stop Effects"),
        base_url=base_url,
    )
