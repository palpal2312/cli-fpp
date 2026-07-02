"""Thin facade for external agents and MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cli_fpp.core import doctor as doctor_mod
from cli_fpp.core import experience_contrib as contrib_mod
from cli_fpp.core import guide
from cli_fpp.core import media
from cli_fpp.core import media_intake
from cli_fpp.core import playlist
from cli_fpp.core import project
from cli_fpp.core import target_setup
from cli_fpp.core import dev_target


def _activate_target(target_name: str | None) -> None:
    if target_name:
        project.set_active_target(target_name)


def _base_url(target_name: str | None = None) -> str:
    _activate_target(target_name)
    return project.get_connection()


def list_targets(*, mask_secrets: bool = True) -> dict[str, Any]:
    """Saved FPP targets on controller."""
    return dev_target.list_targets(mask_secrets=mask_secrets)


def audit_targets(*, persist: bool = True) -> dict[str, Any]:
    """Check FPP version on every target."""
    return target_setup.audit_all_targets(persist=persist)


def suggest(prompt: str, *, target_name: str | None = None) -> dict[str, Any]:
    """Natural-language → proposed CLI steps."""
    return guide.suggest(prompt, target_name=target_name)


def get_guide(topic: str) -> dict[str, Any]:
    """Topic guide (playlist, campaign, media_upload, …)."""
    return guide.get_guide(topic)


def run_doctor(*, include_target: bool = False, fix: bool = False) -> dict[str, Any]:
    """Controller health (python, git, gh, config, contrib)."""
    return doctor_mod.run_doctor(include_target=include_target, fix=fix)


def contrib_queue_status() -> dict[str, Any]:
    """Pending experience contributions."""
    return contrib_mod.queue_status()


def propose_media(
    sources: list[str],
    *,
    target_name: str | None = None,
) -> dict[str, Any]:
    """Inspect creative before upload (portrait, rotate)."""
    _activate_target(target_name)
    return media_intake.propose_media(sources)


def upload_media(
    path: str,
    *,
    target_name: str | None = None,
    auto_orient: bool = True,
) -> dict[str, Any]:
    """Upload one image/video to active target."""
    base_url = _base_url(target_name)
    return media.upload_prepared(path, auto_orient=auto_orient, base_url=base_url)


def play_playlist(
    name: str,
    *,
    repeat: bool = False,
    target_name: str | None = None,
) -> Any:
    """Start playlist on target."""
    base_url = _base_url(target_name)
    return playlist.play(name, repeat=repeat, base_url=base_url)


def tool_schema() -> list[dict[str, Any]]:
    """JSON tool definitions for LLM orchestration."""
    return [
        {
            "name": "cli_fpp_list_targets",
            "description": "List saved FPP targets on controller (~/.cli-fpp).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "cli_fpp_audit_targets",
            "description": "Audit FPP version and connectivity for all targets.",
            "parameters": {
                "type": "object",
                "properties": {"persist": {"type": "boolean", "default": True}},
                "required": [],
            },
        },
        {
            "name": "cli_fpp_suggest",
            "description": "Map user prompt to proposed CLI + web UI steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "target_name": {"type": "string"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "cli_fpp_propose_media",
            "description": "Propose upload (orientation) before sending creative.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "target_name": {"type": "string"},
                },
                "required": ["sources"],
            },
        },
        {
            "name": "cli_fpp_upload_media",
            "description": "Upload image/video to FPP file manager.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "target_name": {"type": "string"},
                    "auto_orient": {"type": "boolean", "default": True},
                },
                "required": ["path"],
            },
        },
        {
            "name": "cli_fpp_play_playlist",
            "description": "Play named playlist on target.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "repeat": {"type": "boolean", "default": False},
                    "target_name": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        {
            "name": "cli_fpp_doctor",
            "description": "Controller diagnostic (pip install, gh auth, targets).",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_target": {"type": "boolean", "default": False},
                    "fix": {"type": "boolean", "default": False},
                },
                "required": [],
            },
        },
    ]


def dispatch_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Run a tool by schema name (for tests / simple agents)."""
    args = arguments or {}
    if name == "cli_fpp_list_targets":
        return list_targets()
    if name == "cli_fpp_audit_targets":
        return audit_targets(persist=bool(args.get("persist", True)))
    if name == "cli_fpp_suggest":
        return suggest(str(args["prompt"]), target_name=args.get("target_name"))
    if name == "cli_fpp_propose_media":
        sources = args.get("sources") or []
        return propose_media([str(s) for s in sources], target_name=args.get("target_name"))
    if name == "cli_fpp_upload_media":
        return upload_media(str(args["path"]), target_name=args.get("target_name"))
    if name == "cli_fpp_play_playlist":
        return play_playlist(
            str(args["name"]),
            repeat=bool(args.get("repeat")),
            target_name=args.get("target_name"),
        )
    if name == "cli_fpp_doctor":
        return run_doctor(
            include_target=bool(args.get("include_target")),
            fix=bool(args.get("fix")),
        )
    raise ValueError(f"Unknown tool: {name}")
