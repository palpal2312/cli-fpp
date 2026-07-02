"""FPP command execution and discovery."""

from __future__ import annotations

from typing import Any

from cli_fpp.utils import fpp_backend as api


def list_commands(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/commands", base_url=base_url)


def get_command_help(command: str, *, base_url: str | None = None) -> Any:
    return api.api_get(f"/api/commands/{command}", base_url=base_url)


def run(command: str, args: list[str] | None = None, *, base_url: str | None = None) -> Any:
    args = args or []
    if not args:
        return api.api_get(api.command_path(command), base_url=base_url)
    from urllib.parse import quote

    return api.api_post(f"/api/command/{quote(command, safe='')}", args, base_url=base_url)


def run_json(payload: dict[str, Any], *, base_url: str | None = None) -> Any:
    return api.api_post("/api/command", payload, base_url=base_url)


def list_presets(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/commandPresets", base_url=base_url)


def trigger_preset(name_or_slot: str, *, base_url: str | None = None) -> Any:
    if name_or_slot.isdigit():
        return api.api_get(
            api.command_path("Trigger Command Preset Slot", name_or_slot),
            base_url=base_url,
        )
    return api.api_get(
        api.command_path("Trigger Command Preset", name_or_slot),
        base_url=base_url,
    )
