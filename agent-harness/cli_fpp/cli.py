"""cli-fpp — Command-line client for Falcon Player.

Wraps the FPP REST API (OpenAPI spec: fpp/www/api/openapi.json).
Runs as a remote client; target a Pi/BBB FPP instance via --url or FPP_BASE_URL.
"""

from __future__ import annotations

import json
import shlex
import sys
from typing import Any

import click
import requests

from cli_fpp import __version__
from cli_fpp.core import commands as cmd_mod
from cli_fpp.core import playlist as playlist_mod
from cli_fpp.core import project
from cli_fpp.core import schedule as schedule_mod
from cli_fpp.core import system as system_mod
from cli_fpp.utils import fpp_backend

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _conn(ctx: click.Context) -> str:
    return ctx.obj["base_url"]


def _json_flag(ctx: click.Context) -> bool:
    return ctx.obj.get("as_json", False)


def output(data: Any, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(data, indent=2, default=str))
    elif isinstance(data, (dict, list)):
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(str(data))


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("--url", default=None, envvar="FPP_BASE_URL", help="FPP instance base URL")
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output")
@click.version_option(version=__version__, prog_name="cli-fpp")
@click.pass_context
def cli(ctx: click.Context, url: str | None, as_json: bool) -> None:
    """CLI harness for Falcon Player (FPP) — REST API remote control."""
    ctx.ensure_object(dict)
    ctx.obj["base_url"] = project.get_connection(url)
    ctx.obj["as_json"] = as_json
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.command("ping")
@click.pass_context
def ping_cmd(ctx: click.Context) -> None:
    """Check connectivity to the FPP instance."""
    data = fpp_backend.ping(base_url=_conn(ctx))
    output(data, _json_flag(ctx))


@cli.group("config")
def config_group() -> None:
    """Local CLI configuration (~/.cli-fpp/config.json)."""


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show saved configuration and active connection."""
    cfg = project.load_config()
    cfg["active_url"] = _conn(ctx)
    output(cfg, _json_flag(ctx))


@config_group.command("set")
@click.argument("key", type=click.Choice(["base_url"]))
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a config value."""
    cfg = project.load_config()
    cfg[key] = value
    path = project.save_config(cfg)
    output({"saved": str(path), key: value}, _json_flag(ctx))


@cli.group("system")
def system_group() -> None:
    """System and fppd status."""


@system_group.command("status")
@click.pass_context
def system_status(ctx: click.Context) -> None:
    """Get FPP system status."""
    output(system_mod.status(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("info")
@click.pass_context
def system_info(ctx: click.Context) -> None:
    """Get FPP system info."""
    output(system_mod.info(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("fppd")
@click.pass_context
def system_fppd(ctx: click.Context) -> None:
    """Get fppd daemon status."""
    output(system_mod.fppd_status(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("version")
@click.pass_context
def system_version(ctx: click.Context) -> None:
    """Get fppd version."""
    output(system_mod.fppd_version(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("restart")
@click.option("--full", is_flag=True, help="Full restart (not quick)")
@click.pass_context
def system_restart(ctx: click.Context, full: bool) -> None:
    """Restart fppd."""
    output(system_mod.fppd_restart(quick=not full, base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("playlist")
def playlist_group() -> None:
    """Playlist management and playback."""


@playlist_group.command("list")
@click.pass_context
def playlist_list(ctx: click.Context) -> None:
    """List playlist names."""
    output(playlist_mod.list_playlists(base_url=_conn(ctx)), _json_flag(ctx))


@playlist_group.command("get")
@click.argument("name")
@click.option("--merge-subs", is_flag=True, help="Merge sub-playlists")
@click.pass_context
def playlist_get(ctx: click.Context, name: str, merge_subs: bool) -> None:
    """Get playlist JSON."""
    output(
        playlist_mod.get_playlist(name, merge_subs=merge_subs, base_url=_conn(ctx)),
        _json_flag(ctx),
    )


@playlist_group.command("play")
@click.argument("name")
@click.option("--start", "start_item", default=1, show_default=True, type=int)
@click.option("--repeat", is_flag=True, help="Repeat playlist")
@click.pass_context
def playlist_play(ctx: click.Context, name: str, start_item: int, repeat: bool) -> None:
    """Start playing a playlist."""
    output(
        playlist_mod.play(name, start_item=start_item, repeat=repeat, base_url=_conn(ctx)),
        _json_flag(ctx),
    )


@playlist_group.command("stop")
@click.option("--now", is_flag=True, help="Stop immediately")
@click.option("--after-loop", is_flag=True, help="Stop after current loop")
@click.pass_context
def playlist_stop(ctx: click.Context, now: bool, after_loop: bool) -> None:
    """Stop the current playlist."""
    output(
        playlist_mod.stop(
            graceful=not now,
            after_loop=after_loop,
            base_url=_conn(ctx),
        ),
        _json_flag(ctx),
    )


@playlist_group.command("next")
@click.pass_context
def playlist_next(ctx: click.Context) -> None:
    """Skip to next playlist item."""
    output(playlist_mod.next_item(base_url=_conn(ctx)), _json_flag(ctx))


@playlist_group.command("prev")
@click.pass_context
def playlist_prev(ctx: click.Context) -> None:
    """Go to previous playlist item."""
    output(playlist_mod.prev_item(base_url=_conn(ctx)), _json_flag(ctx))


@playlist_group.command("pause")
@click.pass_context
def playlist_pause(ctx: click.Context) -> None:
    """Pause playlist."""
    output(playlist_mod.pause(base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("command")
def command_group() -> None:
    """Run FPP commands (maps to /api/command)."""


@command_group.command("list")
@click.pass_context
def command_list(ctx: click.Context) -> None:
    """List available FPP commands."""
    output(cmd_mod.list_commands(base_url=_conn(ctx)), _json_flag(ctx))


@command_group.command("run")
@click.argument("name")
@click.argument("args", nargs=-1)
@click.pass_context
def command_run(ctx: click.Context, name: str, args: tuple[str, ...]) -> None:
    """Run an FPP command by name with optional arguments."""
    output(cmd_mod.run(name, list(args), base_url=_conn(ctx)), _json_flag(ctx))


@command_group.command("preset")
@click.argument("name_or_slot")
@click.pass_context
def command_preset(ctx: click.Context, name_or_slot: str) -> None:
    """Trigger a command preset by name or slot number."""
    output(cmd_mod.trigger_preset(name_or_slot, base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("schedule")
def schedule_group() -> None:
    """Schedule management."""


@schedule_group.command("list")
@click.pass_context
def schedule_list(ctx: click.Context) -> None:
    """List schedules."""
    output(schedule_mod.list_schedules(base_url=_conn(ctx)), _json_flag(ctx))


@schedule_group.command("reload")
@click.pass_context
def schedule_reload(ctx: click.Context) -> None:
    """Reload schedule configuration."""
    output(schedule_mod.reload(base_url=_conn(ctx)), _json_flag(ctx))


@cli.command("repl", hidden=True)
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Interactive REPL (default when no subcommand given)."""
    from cli_fpp.utils.repl_skin import ReplSkin

    skin = ReplSkin("fpp", version=__version__)
    skin.print_banner()
    skin.info(f"Connected to: {_conn(ctx)}")

    pt_session = skin.create_prompt_session()
    commands_dict = {
        "ping": "Check connectivity",
        "system status|info|fppd|version|restart": "System / fppd",
        "playlist list|get|play|stop|next|prev|pause": "Playlist control",
        "command list|run|preset": "FPP commands",
        "schedule list|reload": "Schedules",
        "config show|set": "CLI config",
        "help": "Show commands",
        "quit": "Exit",
    }

    while True:
        try:
            line = skin.get_input(pt_session, project_name=_conn(ctx)).strip()
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            skin.print_goodbye()
            break
        if line.lower() == "help":
            skin.help(commands_dict)
            continue
        try:
            args = shlex.split(line)
        except ValueError:
            args = line.split()
        try:
            cli.main(args, standalone_mode=False, obj=ctx.obj)
        except click.exceptions.UsageError as exc:
            skin.error(str(exc))
        except requests.exceptions.RequestException as exc:
            skin.error(f"HTTP error: {exc}")
        except SystemExit:
            pass
        except Exception as exc:
            skin.error(str(exc))


def main() -> None:
    try:
        cli(obj={})
    except requests.exceptions.RequestException as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
