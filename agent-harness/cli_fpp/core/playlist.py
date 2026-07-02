"""Playlist operations via FPP REST API."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def list_playlists(*, base_url: str | None = None) -> list[str]:
    data = api.api_get("/api/playlists", base_url=base_url)
    if isinstance(data, list):
        return [str(x) for x in data]
    return []


def list_playable(*, base_url: str | None = None) -> Any:
    """Validated playlists — same source as index.php playlist dropdown."""
    return api.api_get("/api/playlists/validate", base_url=base_url)


def get_playlist(name: str, *, merge_subs: bool = False, base_url: str | None = None) -> Any:
    params = {"mergeSubs": "1"} if merge_subs else None
    return api.api_get(f"/api/playlist/{name}", base_url=base_url, params=params)


def play(
    name: str,
    *,
    start_item: int = 1,
    repeat: bool = False,
    base_url: str | None = None,
) -> Any:
    repeat_arg = "true" if repeat else "false"
    path = api.command_path("Start Playlist", name, str(start_item), repeat_arg)
    return api.api_get(path, base_url=base_url)


def stop(*, graceful: bool = True, after_loop: bool = False, base_url: str | None = None) -> Any:
    """Stop via REST — matches index.php StopNow / StopGracefully buttons."""
    if after_loop:
        return api.api_get("/api/playlists/stopgracefullyafterloop", base_url=base_url)
    if graceful:
        return api.api_get("/api/playlists/stopgracefully", base_url=base_url)
    return api.api_get("/api/playlists/stop", base_url=base_url)


def next_item(*, base_url: str | None = None) -> Any:
    return api.api_get(api.command_path("Next Playlist Item"), base_url=base_url)


def prev_item(*, base_url: str | None = None) -> Any:
    return api.api_get(api.command_path("Prev Playlist Item"), base_url=base_url)


def pause(*, base_url: str | None = None) -> Any:
    return api.api_get(api.command_path("Pause Playlist"), base_url=base_url)
