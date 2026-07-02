"""cli-fpp — Command-line client for Falcon Player.

Wraps the FPP REST API (OpenAPI spec: fpp/www/api/openapi.json).
Runs as a remote client; target a Pi/BBB FPP instance via --url or FPP_BASE_URL.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

import click
import requests

from cli_fpp import __version__
from cli_fpp.core import commands as cmd_mod
from cli_fpp.core import experiences as exp_mod
from cli_fpp.core import doctor as doctor_mod
from cli_fpp.core import experience_contrib as contrib_mod
from cli_fpp.core import github_auth as gh_auth_mod
from cli_fpp.core import effects as effects_mod
from cli_fpp.core import gpio as gpio_mod
from cli_fpp.core import guide as guide_mod
from cli_fpp.core import host_ssh as host_mod
from cli_fpp.core import fpp_docker as fpp_mod
from cli_fpp.core import dev_target as target_mod
from cli_fpp.core import target_catalog as catalog_mod
from cli_fpp.core import target_setup as target_setup_mod
from cli_fpp.core import media as media_mod
from cli_fpp.core import image_tools as image_mod
from cli_fpp.core import media_orientation as orient_mod
from cli_fpp.core import media_intake as intake_mod
from cli_fpp.core import video_tools as video_mod
from cli_fpp.core import overlays as overlays_mod
from cli_fpp.core import player as player_mod
from cli_fpp.core import playlist as playlist_mod
from cli_fpp.core import project
from cli_fpp.core import schedule as schedule_mod
from cli_fpp.core import sequence as sequence_mod
from cli_fpp.core import system as system_mod
from cli_fpp.utils import fpp_backend

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _conn(ctx: click.Context) -> str:
    base = ctx.obj.get("base_url")
    if base:
        return base
    return project.get_connection()


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
@click.option("--target", "-t", "target_name", default=None, envvar="FPP_TARGET", help="Named target profile (~/.cli-fpp/config.json)")
@click.option("--user", "-u", "username", default=None, envvar="FPP_USER", help="HTTP Basic Auth username")
@click.option("--password", "-p", "password", default=None, envvar="FPP_PASSWORD", help="HTTP Basic Auth password")
@click.option("--ssh-host", default=None, envvar="FPP_SSH_HOST", help="FPP host SSH (Orange Pi) — display rotation")
@click.option("--ssh-user", default=None, envvar="FPP_SSH_USER", help="SSH username")
@click.option("--ssh-password", default=None, envvar="FPP_SSH_PASSWORD", help="SSH password")
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output")
@click.option("--dry-run", is_flag=True, help="Show what would run without calling FPP API")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip confirmation (use after user/agent confirmed)")
@click.option("--no-setup", is_flag=True, help="Bỏ qua briefing target + kiểm tra phiên bản FPP khi vào REPL")
@click.version_option(version=__version__, prog_name="cli-fpp")
@click.pass_context
def cli(ctx: click.Context, url: str | None, target_name: str | None, username: str | None, password: str | None, ssh_host: str | None, ssh_user: str | None, ssh_password: str | None, as_json: bool, dry_run: bool, assume_yes: bool, no_setup: bool) -> None:
    """Điều khiển FPP song song web UI — hướng dẫn, gợi ý, confirm, rồi thực thi."""
    ctx.ensure_object(dict)
    if target_name:
        project.set_active_target(target_name)
    ctx.obj["target"] = project.get_active_target_name()
    try:
        ctx.obj["base_url"] = project.get_connection(url) if url else project.get_connection()
    except ValueError:
        ctx.obj["base_url"] = url.rstrip("/") if url else None
    if username is not None:
        os.environ["FPP_USER"] = username
    if password is not None:
        os.environ["FPP_PASSWORD"] = password
    if ssh_host is not None:
        os.environ["FPP_SSH_HOST"] = ssh_host
    if ssh_user is not None:
        os.environ["FPP_SSH_USER"] = ssh_user
    if ssh_password is not None:
        os.environ["FPP_SSH_PASSWORD"] = ssh_password
    ctx.obj["as_json"] = as_json
    ctx.obj["dry_run"] = dry_run
    ctx.obj["assume_yes"] = assume_yes
    ctx.obj["skip_setup"] = no_setup
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.command("ping")
@click.pass_context
def ping_cmd(ctx: click.Context) -> None:
    """Check connectivity to the FPP instance."""
    data = fpp_backend.ping(base_url=_conn(ctx))
    output(data, _json_flag(ctx))


@cli.command("doctor")
@click.option("--target", "include_target", is_flag=True, help="Gồm kiểm tra SSH/Docker/FPP trên target (dev doctor)")
@click.option("--compose-dir", default=None)
@click.option("--fix", is_flag=True, help="Tự chạy gh auth login nếu thiếu GitHub auth")
@click.option("--check-only", is_flag=True, help="CI mode: exit 1 khi có check fail")
@click.pass_context
def doctor_cmd(
    ctx: click.Context,
    include_target: bool,
    compose_dir: str | None,
    fix: bool,
    check_only: bool,
) -> None:
    """Kiểm tra controller: Python, git, gh, config, contribute queue (+ tuỳ chọn target)."""
    result = doctor_mod.run_doctor(
        include_target=include_target,
        compose_dir=compose_dir,
        fix=fix,
        check_only=check_only,
    )
    output(result, _json_flag(ctx))
    if result.get("exit_code"):
        raise SystemExit(result["exit_code"])


@cli.group("config")
def config_group() -> None:
    """Local CLI configuration (~/.cli-fpp/config.json)."""


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show saved configuration and active connection."""
    cfg = project.load_config()
    raw = project.load_raw_config()
    cfg["active_url"] = _conn(ctx)
    cfg["active_target"] = ctx.obj.get("target")
    cfg["default_target"] = raw.get("default_target") or None
    cfg["targets"] = project.list_target_names(raw=raw)
    if cfg.get("password"):
        cfg["password"] = "****"
    if cfg.get("ssh_password"):
        cfg["ssh_password"] = "****"
    output(cfg, _json_flag(ctx))


@config_group.command("set")
@click.argument("key", type=click.Choice([
    "base_url", "username", "password",
    "ssh_host", "ssh_user", "ssh_password", "ssh_port",
    "label", "compose_dir", "device_type", "contrib_enabled",
]))
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a config value on the active/default target (or global contrib_enabled)."""
    try:
        if key == "contrib_enabled":
            result = project.set_global_flag(key, value)
        else:
            result = project.set_target_field(ctx.obj.get("target"), key, value)
    except (ValueError, KeyError) as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(2) from exc
    output(result, _json_flag(ctx))


@cli.group("target")
def target_group() -> None:
    """Quản lý nhiều thiết bị FPP từ máy client (remote)."""


@target_group.command("catalog")
@click.pass_context
def target_catalog_cmd(ctx: click.Context) -> None:
    """Phân loại Target (thiết bị) + Player (FPP version)."""
    output(catalog_mod.build_catalog(), _json_flag(ctx))


@target_group.command("device-types")
@click.pass_context
def target_device_types(ctx: click.Context) -> None:
    """Danh sách loại thiết bị Target hỗ trợ."""
    output({"device_types": catalog_mod.list_device_types()}, _json_flag(ctx))


@target_group.command("list")
@click.option("--check-version/--no-check-version", default=False, help="Kiểm tra phiên bản FPP trên mỗi target")
@click.pass_context
def target_list(ctx: click.Context, check_version: bool) -> None:
    """Liệt kê target đã lưu + default/active."""
    data = target_mod.list_targets()
    if check_version:
        data["version_audit"] = target_setup_mod.audit_all_targets()
    output(data, _json_flag(ctx))


@target_group.command("audit")
@click.pass_context
def target_audit(ctx: click.Context) -> None:
    """Kiểm tra phiên bản FPP trên tất cả target-device."""
    output(target_setup_mod.audit_all_targets(), _json_flag(ctx))


@target_group.command("setup")
@click.option("--add-mode", type=click.Choice(["batch", "one"]), default=None, help="1=batch, 2=one")
@click.option("--add-count", type=int, default=None, help="Số target thêm (khi --add-mode batch)")
@click.option("--skip-add", is_flag=True, help="Chỉ thông báo + audit, không hỏi thêm target")
@click.pass_context
def target_setup_cmd(
    ctx: click.Context,
    add_mode: str | None,
    add_count: int | None,
    skip_add: bool,
) -> None:
    """Briefing: số target đang quản lý → thêm (batch/từng cái) → kiểm tra FPP."""
    if _json_flag(ctx):
        output(
            target_setup_mod.run_setup(
                interactive=False,
                add_mode=add_mode,
                add_count=add_count,
                skip_add_prompt=True,
            ),
            True,
        )
        return
    data = target_setup_mod.run_setup(
        interactive=True,
        add_mode=add_mode,
        add_count=add_count,
        skip_add_prompt=skip_add,
    )
    target_setup_mod.print_briefing(data)


@target_group.command("show")
@click.argument("name", required=False)
@click.pass_context
def target_show(ctx: click.Context, name: str | None) -> None:
    """Xem profile một target (mặc định: active/default)."""
    try:
        output(target_mod.target_profile(name=name), _json_flag(ctx))
    except KeyError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@target_group.command("add")
@click.argument("name")
@click.option("--fpp-url", default=None, help="http://192.168.1.39:81")
@click.option("--fpp-user", default=None, help="admin")
@click.option("--fpp-password", default=None, help="HTTP password")
@click.option("--ssh-host", default=None)
@click.option("--ssh-user", default="orangepi", show_default=True)
@click.option("--ssh-password", default=None)
@click.option("--label", default=None, help="Mô tả ngắn (vd. Cửa hàng A)")
@click.option(
    "--device-type",
    type=click.Choice(list(catalog_mod.DEVICE_TYPES.keys())),
    default=None,
    help="Loại Target: orangepi, raspberrypi, bbb, x86, generic",
)
@click.option("--default", "make_default", is_flag=True, help="Đặt làm target mặc định")
@click.pass_context
def target_add(
    ctx: click.Context,
    name: str,
    fpp_url: str | None,
    fpp_user: str | None,
    fpp_password: str | None,
    ssh_host: str | None,
    ssh_user: str | None,
    ssh_password: str | None,
    label: str | None,
    device_type: str | None,
    make_default: bool,
) -> None:
    """Thêm/cập nhật target (FPP URL + SSH cho dev)."""
    try:
        output(
            target_mod.add_target(
                name,
                base_url=fpp_url,
                username=fpp_user,
                password=fpp_password,
                ssh_host=ssh_host,
                ssh_user=ssh_user,
                ssh_password=ssh_password,
                label=label,
                device_type=device_type,
                make_default=make_default,
            ),
            _json_flag(ctx),
        )
    except (ValueError, KeyError) as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(2) from exc


@target_group.command("use")
@click.argument("name")
@click.pass_context
def target_use(ctx: click.Context, name: str) -> None:
    """Chọn target mặc định (lưu vào config)."""
    try:
        output(target_mod.use_target(name), _json_flag(ctx))
    except KeyError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@target_group.command("remove")
@click.argument("name")
@click.pass_context
def target_remove(ctx: click.Context, name: str) -> None:
    """Xóa target khỏi config."""
    try:
        output(target_mod.remove_target(name), _json_flag(ctx))
    except KeyError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@cli.group("guide")
def guide_group() -> None:
    """Hướng dẫn sử dụng FPP qua CLI và web UI."""


@guide_group.command("topics")
@click.pass_context
def guide_topics(ctx: click.Context) -> None:
    """Liệt kê chủ đề hướng dẫn."""
    output({"topics": guide_mod.list_topics()}, _json_flag(ctx))


@guide_group.command("show")
@click.argument("topic")
@click.pass_context
def guide_show(ctx: click.Context, topic: str) -> None:
    """Chi tiết hướng dẫn: start, playlist, volume, schedule, system, display."""
    output(guide_mod.get_guide(topic), _json_flag(ctx))


@cli.command("suggest")
@click.argument("prompt", nargs=-1, required=True)
@click.pass_context
def suggest_cmd(ctx: click.Context, prompt: tuple[str, ...]) -> None:
    """Đọc prompt tự nhiên → đề xuất lệnh CLI + cách làm trên web UI + câu confirm."""
    text = " ".join(prompt)
    output(guide_mod.suggest(text, target_name=ctx.obj.get("target")), _json_flag(ctx))


@cli.group("experience")
def experience_group() -> None:
    """Kinh nghiệm theo Target (device) và Player (FPP version)."""


@experience_group.command("list")
@click.option("--target", "target_name", default=None, help="Target profile (mặc định: active)")
@click.option("--device-type", default=None)
@click.option("--player-line", default=None)
@click.option("--tag", default=None)
@click.option("--all-scopes", is_flag=True, help="Hiện cả entry device/player không khớp context")
@click.pass_context
def experience_list(
    ctx: click.Context,
    target_name: str | None,
    device_type: str | None,
    player_line: str | None,
    tag: str | None,
    all_scopes: bool,
) -> None:
    """Liệt kê kinh nghiệm theo 3 tầng: chung / riêng device / riêng player."""
    output(
        exp_mod.list_experiences(
            target_name=target_name or ctx.obj.get("target"),
            device_type=device_type,
            player_line=player_line,
            tag=tag,
            include_non_matching=all_scopes,
        ),
        _json_flag(ctx),
    )


@experience_group.command("catalog")
@click.option("--target", "target_name", default=None)
@click.pass_context
def experience_catalog(ctx: click.Context, target_name: str | None) -> None:
    """Phân loại kinh nghiệm theo device_type + player_line."""
    output(
        exp_mod.catalog_summary(target_name=target_name or ctx.obj.get("target")),
        _json_flag(ctx),
    )


@experience_group.command("show")
@click.argument("entry_id")
@click.pass_context
def experience_show(ctx: click.Context, entry_id: str) -> None:
    """Chi tiết một kinh nghiệm."""
    try:
        output(exp_mod.get_experience(entry_id, target_name=ctx.obj.get("target")), _json_flag(ctx))
    except KeyError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@experience_group.command("add")
@click.option("--title", required=True)
@click.option("--body", required=True)
@click.option(
    "--scope",
    type=click.Choice(exp_mod.SCOPES),
    default=exp_mod.SCOPE_GLOBAL,
)
@click.option("--device-type", default=None)
@click.option("--player-line", default=None)
@click.option("--player-version", default=None)
@click.option("--target", "target_name", default=None)
@click.option("--tag", multiple=True)
@click.pass_context
def experience_add(
    ctx: click.Context,
    title: str,
    body: str,
    scope: str,
    device_type: str | None,
    player_line: str | None,
    player_version: str | None,
    target_name: str | None,
    tag: tuple[str, ...],
) -> None:
    """Thêm kinh nghiệm (global / device / player)."""
    try:
        output(
            exp_mod.add_experience(
                title=title,
                body=body,
                scope=scope,
                device_type=device_type,
                player_line=player_line,
                player_version=player_version,
                target_name=target_name,
                tags=list(tag),
            ),
            _json_flag(ctx),
        )
    except ValueError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(2) from exc


@experience_group.command("remember")
@click.argument("text")
@click.option("--title", default=None)
@click.option("--target", "target_name", default=None)
@click.option("--scope", type=click.Choice(exp_mod.SCOPES), default=None, help="global|device|player — mặc định tự chọn")
@click.option("--tag", multiple=True)
@click.pass_context
def experience_remember(
    ctx: click.Context,
    text: str,
    title: str | None,
    target_name: str | None,
    scope: str | None,
    tag: tuple[str, ...],
) -> None:
    """Ghi nhớ — chọn tầng: chung / riêng device / riêng player."""
    try:
        output(
            exp_mod.remember_experience(
                text,
                title=title,
                target_name=target_name or ctx.obj.get("target"),
                tags=list(tag),
                scope=scope,
            ),
            _json_flag(ctx),
        )
    except ValueError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(2) from exc


@experience_group.command("remove")
@click.argument("entry_id")
@click.pass_context
def experience_remove(ctx: click.Context, entry_id: str) -> None:
    """Xóa kinh nghiệm do user thêm (không xóa bundled)."""
    try:
        output(exp_mod.remove_experience(entry_id), _json_flag(ctx))
    except (KeyError, ValueError) as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@experience_group.group("contribute")
def experience_contribute_group() -> None:
    """Đóng góp kinh nghiệm từ máy user về repo (queue local → inbox PR)."""


@experience_contribute_group.command("status")
@click.pass_context
def experience_contribute_status(ctx: click.Context) -> None:
    """Trạng thái hàng đợi contribute (~/.cli-fpp/contrib_queue.jsonl)."""
    output(contrib_mod.queue_status(), _json_flag(ctx))


@experience_contribute_group.command("login")
@click.pass_context
def experience_contribute_login(ctx: click.Context) -> None:
    """Đăng nhập GitHub qua gh auth login (web browser)."""
    try:
        output(gh_auth_mod.login(), _json_flag(ctx))
    except gh_auth_mod.GitHubAuthError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(2) from exc


@experience_contribute_group.command("export")
@click.option("--out", "out_path", type=click.Path(), default=None, help="Ghi JSON ra file")
@click.pass_context
def experience_contribute_export(ctx: click.Context, out_path: str | None) -> None:
    """Export entry pending (stdout hoặc --out)."""
    payload = contrib_mod.export_pending(mark_exported=bool(out_path))
    if out_path:
        Path(out_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        output({"exported": out_path, "entry_count": payload["entry_count"]}, _json_flag(ctx))
    else:
        output(payload, True)


@experience_contribute_group.command("submit")
@click.option("--repo", "repo_root", default=None, help="Clone local → inbox/ (không cần GitHub)")
@click.option("--github", "use_github", is_flag=True, help="Fork + PR qua gh API (khuyến nghị)")
@click.option("--upstream", default=None, help="owner/repo upstream (mặc định CLI_FPP_GITHUB_REPO)")
@click.pass_context
def experience_contribute_submit(
    ctx: click.Context,
    repo_root: str | None,
    use_github: bool,
    upstream: str | None,
) -> None:
    """Gửi pending: --github (PR) hoặc ghi file inbox local."""
    try:
        if use_github:
            output(contrib_mod.submit_via_github(upstream), _json_flag(ctx))
        else:
            output(contrib_mod.submit_to_repo(repo_root), _json_flag(ctx))
    except (FileNotFoundError, gh_auth_mod.GitHubAuthError, ValueError) as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(2) from exc


@experience_contribute_group.command("promote")
@click.option("--limit", default=10, show_default=True)
@click.pass_context
def experience_contribute_promote(ctx: click.Context, limit: int) -> None:
    """Copy queue pending vào ~/.cli-fpp/experiences.json (không cần PR)."""
    output(contrib_mod.promote_to_local_experiences(limit=limit), _json_flag(ctx))


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
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result(
                "system.restart",
                {"quick": not full, "base_url": _conn(ctx)},
            ),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Khởi động lại fppd? Show đang chạy có thể bị gián đoạn.",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "system.restart"}, _json_flag(ctx))
        return
    output(system_mod.fppd_restart(quick=not full, base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("volume")
@click.argument("level", required=False, type=click.IntRange(0, 100))
@click.pass_context
def system_volume(ctx: click.Context, level: int | None) -> None:
    """Get or set volume (index.php slider)."""
    if level is None:
        output(system_mod.volume_get(base_url=_conn(ctx)), _json_flag(ctx))
        return
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("system.volume", {"level": level}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, f"Đặt volume = {level}?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "system.volume"}, _json_flag(ctx))
        return
    output(system_mod.volume_set(level, base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("fppd-start")
@click.pass_context
def system_fppd_start(ctx: click.Context) -> None:
    """Start fppd daemon (ControlFPPD button)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("system.fppd_start", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Khởi động fppd?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "system.fppd_start"}, _json_flag(ctx))
        return
    output(system_mod.fppd_start(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("fppd-stop")
@click.pass_context
def system_fppd_stop(ctx: click.Context) -> None:
    """Stop fppd daemon."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("system.fppd_stop", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Dừng fppd? Show sẽ ngừng.", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "system.fppd_stop"}, _json_flag(ctx))
        return
    output(system_mod.fppd_stop(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("reboot")
@click.pass_context
def system_reboot(ctx: click.Context) -> None:
    """Reboot the FPP host."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("system.reboot", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Reboot máy FPP?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "system.reboot"}, _json_flag(ctx))
        return
    output(system_mod.reboot(base_url=_conn(ctx)), _json_flag(ctx))


@system_group.command("shutdown")
@click.pass_context
def system_shutdown(ctx: click.Context) -> None:
    """Shutdown the FPP host."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("system.shutdown", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Tắt máy FPP?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "system.shutdown"}, _json_flag(ctx))
        return
    output(system_mod.shutdown(base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("player")
def player_group() -> None:
    """Player status — what is playing now (index.php)."""


@player_group.command("status")
@click.pass_context
def player_status(ctx: click.Context) -> None:
    """Detailed player status."""
    output(player_mod.status(base_url=_conn(ctx)), _json_flag(ctx))


@player_group.command("current")
@click.pass_context
def player_current(ctx: click.Context) -> None:
    """Current playlist info."""
    output(player_mod.current(base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("playlist")
def playlist_group() -> None:
    """Playlist management and playback."""


@playlist_group.command("list")
@click.option("--playable", is_flag=True, help="Validated playlists (index.php dropdown)")
@click.pass_context
def playlist_list(ctx: click.Context, playable: bool) -> None:
    """List playlist names."""
    if playable:
        output(playlist_mod.list_playable(base_url=_conn(ctx)), _json_flag(ctx))
    else:
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
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result(
                "playlist.play",
                {"name": name, "start_item": start_item, "repeat": repeat},
            ),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        f"Phát playlist '{name}'" + (" (lặp lại)" if repeat else "") + "?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "playlist.play", "name": name}, _json_flag(ctx))
        return
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
    mode = "now" if now else ("after_loop" if after_loop else "graceful")
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result("playlist.stop", {"mode": mode}),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Dừng playlist đang chạy?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "playlist.stop"}, _json_flag(ctx))
        return
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
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("playlist.next", {}), _json_flag(ctx))
        return
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
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("playlist.pause", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Tạm dừng playlist?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "playlist.pause"}, _json_flag(ctx))
        return
    output(playlist_mod.pause(base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("command")
def command_group() -> None:
    """Run FPP commands (maps to /api/command)."""


@command_group.command("list")
@click.pass_context
def command_list(ctx: click.Context) -> None:
    """List available FPP commands."""
    output(cmd_mod.list_commands(base_url=_conn(ctx)), _json_flag(ctx))


@command_group.command("help")
@click.argument("name")
@click.pass_context
def command_help(ctx: click.Context, name: str) -> None:
    """Help for a specific FPP command."""
    output(cmd_mod.get_command_help(name, base_url=_conn(ctx)), _json_flag(ctx))


@command_group.command("presets")
@click.pass_context
def command_presets(ctx: click.Context) -> None:
    """List command presets."""
    output(cmd_mod.list_presets(base_url=_conn(ctx)), _json_flag(ctx))


@command_group.command("run")
@click.argument("name")
@click.argument("args", nargs=-1)
@click.pass_context
def command_run(ctx: click.Context, name: str, args: tuple[str, ...]) -> None:
    """Run an FPP command by name with optional arguments."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result("command.run", {"name": name, "args": list(args)}),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        f'Chạy lệnh FPP "{name}"?',
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "command.run", "name": name}, _json_flag(ctx))
        return
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
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("schedule.reload", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Reload lịch phát?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "schedule.reload"}, _json_flag(ctx))
        return
    output(schedule_mod.reload(base_url=_conn(ctx)), _json_flag(ctx))


@schedule_group.command("extend")
@click.argument("seconds", type=int)
@click.pass_context
def schedule_extend(ctx: click.Context, seconds: int) -> None:
    """Extend current scheduled playlist (scheduler.php)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("schedule.extend", {"seconds": seconds}), _json_flag(ctx))
        return
    output(schedule_mod.extend(seconds, base_url=_conn(ctx)), _json_flag(ctx))


@schedule_group.command("next")
@click.pass_context
def schedule_next(ctx: click.Context) -> None:
    """Force-start next scheduled item."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("schedule.next", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Bắt đầu mục lịch tiếp theo?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "schedule.next"}, _json_flag(ctx))
        return
    output(schedule_mod.start_next(base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("media")
def media_group() -> None:
    """Media and sequence files (file manager / playlist editor)."""


@media_group.command("list")
@click.pass_context
def media_list(ctx: click.Context) -> None:
    """List media files."""
    output(media_mod.list_media(base_url=_conn(ctx)), _json_flag(ctx))


@media_group.command("sequences")
@click.pass_context
def media_sequences(ctx: click.Context) -> None:
    """List sequence (.fseq) files."""
    output(media_mod.list_sequences(base_url=_conn(ctx)), _json_flag(ctx))


@media_group.command("duration")
@click.argument("file")
@click.pass_context
def media_duration(ctx: click.Context, file: str) -> None:
    """Get media file duration."""
    output(media_mod.media_duration(file, base_url=_conn(ctx)), _json_flag(ctx))


def _resolve_media_profile(ctx: click.Context, auto_orient: bool) -> dict | None:
    if not auto_orient:
        return None
    try:
        return orient_mod.get_display_profile()
    except (ValueError, RuntimeError, OSError) as exc:
        if _json_flag(ctx):
            output({"warning": f"Không lấy được display profile qua SSH: {exc}"}, True)
        else:
            click.echo(f"Cảnh báo: không lấy display profile — {exc}", err=True)
        return None


@media_group.command("display-profile")
@click.pass_context
def media_display_profile(ctx: click.Context) -> None:
    """Khung hiển thị thiết bị (SSH) — portrait/landscape, canvas fb0."""
    output(orient_mod.get_display_profile(), _json_flag(ctx))


@media_group.command("propose")
@click.argument("sources", nargs=-1, required=True)
@click.option(
    "--rotate",
    type=click.Choice(["auto", "0", "90", "180", "270"]),
    default="auto",
    show_default=True,
)
@click.pass_context
def media_propose(ctx: click.Context, sources: tuple[str, ...], rotate: str) -> None:
    """Kiểm tra thiết bị + ảnh (file/URL) → đề xuất xoay trước upload (không upload)."""
    profile = _resolve_media_profile(ctx, True)
    rot: orient_mod.RotateArg = "auto" if rotate == "auto" else int(rotate)  # type: ignore[assignment]
    output(
        intake_mod.propose_media(list(sources), display_profile=profile, rotate=rot),
        _json_flag(ctx),
    )


@media_group.command("fetch")
@click.argument("url")
@click.option(
    "--dest",
    type=click.Path(path_type=Path),
    default=None,
    help="Thư mục lưu (mặc định agent-harness/.uploads)",
)
@click.pass_context
def media_fetch(ctx: click.Context, url: str, dest: Path | None) -> None:
    """Tải ảnh từ URL về local (để agent upload sau)."""
    if not intake_mod.is_url(url):
        raise click.ClickException("URL phải bắt đầu bằng http:// hoặc https://")
    out_dir = dest or (Path("agent-harness") / ".uploads")
    path, meta = intake_mod.fetch_source(url, dest_dir=out_dir)
    output({**meta, "saved_to": str(path)}, _json_flag(ctx))


@media_group.command("prepare-images")
@click.argument("src", type=click.Path(exists=True, path_type=Path))
@click.argument("dst", type=click.Path(path_type=Path))
@click.option("--width", type=int, default=0, help="Output width (0 = theo canvas thiết bị hoặc 1920)")
@click.option("--height", type=int, default=0, help="Output height (0 = theo canvas thiết bị hoặc 1080)")
@click.option(
    "--rotate",
    type=click.Choice(["auto", "0", "90", "180", "270"]),
    default="auto",
    show_default=True,
    help="auto = transpose khi màn portrait + ảnh dọc",
)
@click.option("--auto-orient/--no-auto-orient", default=True, help="SSH kiểm tra portrait trước khi xử lý")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files in dst")
@click.pass_context
def media_prepare_images(
    ctx: click.Context,
    src: Path,
    dst: Path,
    width: int,
    height: int,
    rotate: str,
    auto_orient: bool,
    overwrite: bool,
) -> None:
    """Rotate + resize ảnh local trước khi upload FPP."""
    profile = _resolve_media_profile(ctx, auto_orient)
    w = width or int((profile or {}).get("canvas_width") or 1920)
    h = height or int((profile or {}).get("canvas_height") or 1080)
    rot: orient_mod.RotateArg = "auto" if rotate == "auto" else int(rotate)  # type: ignore[assignment]
    result = image_mod.prepare_images(
        src,
        dst,
        width=w,
        height=h,
        rotate=rot,
        display_profile=profile if auto_orient else None,
        overwrite=overwrite,
    )
    out = result.to_dict()
    if profile:
        out["display_profile"] = profile
    output(out, _json_flag(ctx))


@media_group.command("prepare-videos")
@click.argument("src", type=click.Path(exists=True, path_type=Path))
@click.argument("dst", type=click.Path(path_type=Path))
@click.option("--width", type=int, default=0, help="Output width (0 = theo canvas thiết bị hoặc 1920)")
@click.option("--height", type=int, default=0, help="Output height (0 = theo canvas thiết bị hoặc 1080)")
@click.option(
    "--rotate",
    type=click.Choice(["auto", "0", "90", "180", "270"]),
    default="auto",
    show_default=True,
    help="auto = transpose khi màn portrait + video dọc",
)
@click.option("--auto-orient/--no-auto-orient", default=True, help="SSH kiểm tra portrait trước khi xử lý")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files in dst")
@click.pass_context
def media_prepare_videos(
    ctx: click.Context,
    src: Path,
    dst: Path,
    width: int,
    height: int,
    rotate: str,
    auto_orient: bool,
    overwrite: bool,
) -> None:
    """Transpose + scale video (ffmpeg) trước khi upload FPP."""
    profile = _resolve_media_profile(ctx, auto_orient)
    w = width or int((profile or {}).get("canvas_width") or 1920)
    h = height or int((profile or {}).get("canvas_height") or 1080)
    rot: orient_mod.RotateArg = "auto" if rotate == "auto" else int(rotate)  # type: ignore[assignment]
    result = video_mod.prepare_videos(
        src,
        dst,
        width=w,
        height=h,
        rotate=rot,
        display_profile=profile if auto_orient else None,
        overwrite=overwrite,
    )
    out = result.to_dict()
    if profile:
        out["display_profile"] = profile
    output(out, _json_flag(ctx))


@media_group.command("upload")
@click.argument("src")
@click.option("--dir", "dirname", default=None, help="FPP dir: images|videos (mặc định theo loại file)")
@click.option(
    "--rotate",
    type=click.Choice(["auto", "0", "90", "180", "270"]),
    default="auto",
    show_default=True,
)
@click.option("--auto-orient/--no-auto-orient", default=True, help="Tự transpose nếu màn portrait + media dọc")
@click.option("--skip-propose", is_flag=True, help="Upload thẳng, bỏ bước đề xuất (không khuyến nghị)")
@click.option("--width", type=int, default=0)
@click.option("--height", type=int, default=0)
@click.pass_context
def media_upload(
    ctx: click.Context,
    src: str,
    dirname: str | None,
    rotate: str,
    auto_orient: bool,
    skip_propose: bool,
    width: int,
    height: int,
) -> None:
    """Chuẩn bị (propose → transpose) rồi upload ảnh/video lên FPP (file, folder hoặc URL)."""
    if not intake_mod.is_url(src) and not Path(src).exists():
        raise click.ClickException(f"Không tìm thấy file: {src}")

    rot: orient_mod.RotateArg = "auto" if rotate == "auto" else int(rotate)  # type: ignore[assignment]
    profile = _resolve_media_profile(ctx, auto_orient)
    w = width or int((profile or {}).get("canvas_width") or 1920)
    h = height or int((profile or {}).get("canvas_height") or 1080)

    proposal: dict | None = None
    if not skip_propose and auto_orient:
        try:
            proposal = intake_mod.propose_media([src], display_profile=profile, rotate=rot)
        except (ValueError, RuntimeError, OSError) as exc:
            if _json_flag(ctx):
                output({"warning": f"propose failed: {exc}"}, True)
            else:
                click.echo(f"Cảnh báo propose: {exc}", err=True)

    if confirm_mod.is_dry_run(ctx.obj):
        output(
            proposal
            or confirm_mod.dry_run_result(
                "media.upload",
                {"src": str(src), "dirname": dirname, "auto_orient": auto_orient, "rotate": rotate},
            ),
            _json_flag(ctx),
        )
        return

    confirm_hint = proposal.get("summary", "") if proposal else ""
    confirm_q = f"Upload media từ '{src}' lên FPP?"
    if confirm_hint:
        confirm_q = f"{confirm_hint}. Tiếp tục upload?"
    if not confirm_mod.require_confirm(ctx.obj, confirm_q, as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "media.upload", "proposal": proposal}, _json_flag(ctx))
        return

    result = media_mod.upload_prepared(
        src,
        dirname=dirname,
        auto_orient=auto_orient,
        rotate=rot,
        width=w,
        height=h,
        base_url=_conn(ctx),
        display_profile=profile,
    )
    if proposal:
        result["proposal"] = {
            "device": proposal.get("device"),
            "summary": proposal.get("summary"),
            "items": proposal.get("items"),
            "recommendation": proposal.get("recommendation"),
        }
    output(result, _json_flag(ctx))


@cli.group("sequence")
def sequence_group() -> None:
    """Sequence transport (index.php pause/step)."""


@sequence_group.command("pause")
@click.pass_context
def sequence_pause(ctx: click.Context) -> None:
    """Toggle sequence pause/resume (ToggleSequencePause)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("sequence.pause", {}), _json_flag(ctx))
        return
    output(sequence_mod.toggle_pause(base_url=_conn(ctx)), _json_flag(ctx))


@sequence_group.command("step")
@click.pass_context
def sequence_step(ctx: click.Context) -> None:
    """Step paused sequence one frame."""
    output(sequence_mod.step(base_url=_conn(ctx)), _json_flag(ctx))


@sequence_group.command("stop")
@click.pass_context
def sequence_stop(ctx: click.Context) -> None:
    """Stop current sequence."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("sequence.stop", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Dừng sequence?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "sequence.stop"}, _json_flag(ctx))
        return
    output(sequence_mod.stop(base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("effects")
def effects_group() -> None:
    """Effects (effects.php)."""


@effects_group.command("list")
@click.pass_context
def effects_list(ctx: click.Context) -> None:
    """List available effects."""
    output(effects_mod.list_effects(base_url=_conn(ctx)), _json_flag(ctx))


@effects_group.command("running")
@click.pass_context
def effects_running(ctx: click.Context) -> None:
    """List running effects."""
    output(effects_mod.running(base_url=_conn(ctx)), _json_flag(ctx))


@effects_group.command("start")
@click.argument("name")
@click.option("--channel", default=0, show_default=True, type=int)
@click.option("--loop", is_flag=True)
@click.option("--background", is_flag=True)
@click.option("--fseq", is_flag=True, help="FSEQ effect instead of eseq")
@click.pass_context
def effects_start(ctx: click.Context, name: str, channel: int, loop: bool, background: bool, fseq: bool) -> None:
    """Start an effect."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result("effects.start", {"name": name, "fseq": fseq}),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(ctx.obj, f"Bắt đầu effect '{name}'?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "effects.start"}, _json_flag(ctx))
        return
    output(
        effects_mod.start(
            name,
            channel=channel,
            loop=loop,
            background=background,
            fseq=fseq,
            base_url=_conn(ctx),
        ),
        _json_flag(ctx),
    )


@effects_group.command("stop")
@click.argument("name", required=False)
@click.pass_context
def effects_stop(ctx: click.Context, name: str | None) -> None:
    """Stop running effect(s)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("effects.stop", {"name": name}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, "Dừng effect?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "effects.stop"}, _json_flag(ctx))
        return
    output(effects_mod.stop(name, base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("overlays")
def overlays_group() -> None:
    """Pixel overlays (pixeloverlaymodels.php)."""


@overlays_group.command("models")
@click.pass_context
def overlays_models(ctx: click.Context) -> None:
    """List overlay models."""
    output(overlays_mod.models(base_url=_conn(ctx)), _json_flag(ctx))


@overlays_group.command("running")
@click.pass_context
def overlays_running(ctx: click.Context) -> None:
    """List running overlay effects."""
    output(overlays_mod.running(base_url=_conn(ctx)), _json_flag(ctx))


@overlays_group.command("settings")
@click.pass_context
def overlays_settings(ctx: click.Context) -> None:
    """Overlay settings."""
    output(overlays_mod.settings(base_url=_conn(ctx)), _json_flag(ctx))


@overlays_group.command("stop")
@click.argument("model")
@click.pass_context
def overlays_stop(ctx: click.Context, model: str) -> None:
    """Stop all effects on an overlay model."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("overlays.stop", {"model": model}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, f"Dừng overlay trên '{model}'?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "overlays.stop"}, _json_flag(ctx))
        return
    output(overlays_mod.stop_model_effects(model, base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("gpio")
def gpio_group() -> None:
    """GPIO pin control."""


@gpio_group.command("list")
@click.option("--names-only", is_flag=True)
@click.pass_context
def gpio_list(ctx: click.Context, names_only: bool) -> None:
    """List GPIO pins."""
    output(gpio_mod.list_pins(names_only=names_only, base_url=_conn(ctx)), _json_flag(ctx))


@gpio_group.command("get")
@click.argument("pin")
@click.pass_context
def gpio_get(ctx: click.Context, pin: str) -> None:
    """Read GPIO pin value."""
    output(gpio_mod.get_pin(pin, base_url=_conn(ctx)), _json_flag(ctx))


@gpio_group.command("set")
@click.argument("pin")
@click.argument("value", type=click.IntRange(0, 1))
@click.pass_context
def gpio_set(ctx: click.Context, pin: str, value: int) -> None:
    """Set GPIO pin output (0 or 1)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("gpio.set", {"pin": pin, "value": value}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(ctx.obj, f"GPIO {pin} = {value}?", as_json=_json_flag(ctx)):
        output({"cancelled": True, "action": "gpio.set"}, _json_flag(ctx))
        return
    output(gpio_mod.set_pin(pin, value, base_url=_conn(ctx)), _json_flag(ctx))


@cli.group("dev")
def dev_group() -> None:
    """Triển khai Orange Pi / FPP — SSH, display, Docker, build (không dùng cho đổi nội dung hàng ngày)."""


@dev_group.command("doctor")
@click.option("--compose-dir", default=None)
@click.pass_context
def dev_doctor_cmd(ctx: click.Context, compose_dir: str | None) -> None:
    """Kiểm tra config, SSH, Docker, FPP API — gợi ý bước tiếp theo."""
    output(target_mod.dev_doctor(compose_dir=compose_dir), _json_flag(ctx))


@dev_group.group("target")
def dev_target_group() -> None:
    """Profile thiết bị target (FPP URL + SSH)."""


@dev_target_group.command("show")
@click.pass_context
def dev_target_show(ctx: click.Context) -> None:
    """Xem target đang cấu hình (~/.cli-fpp/config.json)."""
    output(target_mod.target_profile(), _json_flag(ctx))


@dev_target_group.command("init")
@click.option("--name", default=None, help="Tên target (vd. shop-a); mặc định: default")
@click.option("--fpp-url", default=None, help="http://192.168.1.39:81")
@click.option("--fpp-user", default=None, help="admin")
@click.option("--fpp-password", default=None, help="HTTP password")
@click.option("--ssh-host", default=None)
@click.option("--ssh-user", default="orangepi", show_default=True)
@click.option("--ssh-password", default=None)
@click.option("--device-type", type=click.Choice(list(catalog_mod.DEVICE_TYPES.keys())), default=None)
@click.option("--default", "make_default", is_flag=True, help="Đặt làm target mặc định")
@click.pass_context
def dev_target_init(
    ctx: click.Context,
    name: str | None,
    fpp_url: str | None,
    fpp_user: str | None,
    fpp_password: str | None,
    ssh_host: str | None,
    ssh_user: str | None,
    ssh_password: str | None,
    device_type: str | None,
    make_default: bool,
) -> None:
    """Lưu target profile (alias của target add)."""
    if not any([fpp_url, fpp_user, fpp_password, ssh_host, ssh_password]):
        output(
            {
                "error": "Cần ít nhất một field",
                "example": (
                    "cli-fpp target add shop-a "
                    "--fpp-url http://192.168.1.39:81 --fpp-user admin --fpp-password *** "
                    "--ssh-host 192.168.1.39 --ssh-user orangepi --ssh-password ***"
                ),
            },
            _json_flag(ctx),
        )
        raise SystemExit(2)
    output(
        target_mod.save_target(
            name=name,
            base_url=fpp_url,
            username=fpp_user,
            password=fpp_password,
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password,
            device_type=device_type,
            make_default=make_default,
        ),
        _json_flag(ctx),
    )


@dev_group.group("fpp")
def dev_fpp_group() -> None:
    """Cài đặt, build, deploy FPP Docker trên Orange Pi (SSH)."""


@dev_fpp_group.command("status")
@click.option("--compose-dir", default=None, help="Thư mục docker-compose trên host")
@click.pass_context
def dev_fpp_status(ctx: click.Context, compose_dir: str | None) -> None:
    """Trạng thái compose, image, container, VirtualMatrix."""
    output(fpp_mod.fpp_status(compose_dir=compose_dir), _json_flag(ctx))


@dev_fpp_group.command("install")
@click.option("--compose-dir", default=None, help="Mặc định /home/orangepi/fpp/Docker")
@click.option("--http-port", default=81, show_default=True, type=int)
@click.option("--mount-source/--no-mount-source", default=False, help="Mount ./fpp → /opt/fpp")
@click.option("--pull/--no-pull", default=True, help="docker-compose pull trước khi up")
@click.option("--autostart/--no-autostart", default=True, help="Cài systemd fpp-docker.service")
@click.option("--force", is_flag=True, help="Ghi đè docker-compose.yml đã có")
@click.pass_context
def dev_fpp_install(
    ctx: click.Context,
    compose_dir: str | None,
    http_port: int,
    mount_source: bool,
    pull: bool,
    autostart: bool,
    force: bool,
) -> None:
    """Tạo compose + media, pull image, docker-compose up -d."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result(
                "dev.fpp.install",
                {"compose_dir": compose_dir, "http_port": http_port, "mount_source": mount_source},
            ),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        f"Cài FPP Docker (port {http_port}) trên Orange Pi?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.fpp.install"}, _json_flag(ctx))
        return
    try:
        output(
            fpp_mod.fpp_install(
                compose_dir=compose_dir,
                http_port=http_port,
                mount_source=mount_source,
                pull=pull,
                autostart=autostart,
                force=force,
            ),
            _json_flag(ctx),
        )
    except ValueError as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@dev_fpp_group.command("down")
@click.option("--compose-dir", default=None)
@click.pass_context
def dev_fpp_down(ctx: click.Context, compose_dir: str | None) -> None:
    """docker-compose down — dừng FPP trên target."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("dev.fpp.down", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Dừng container FPP (docker-compose down)?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.fpp.down"}, _json_flag(ctx))
        return
    output(fpp_mod.fpp_down(compose_dir=compose_dir), _json_flag(ctx))


@dev_fpp_group.command("bootstrap")
@click.option("--source", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
@click.option("--compose-dir", default=None)
@click.option("--http-port", default=81, show_default=True, type=int)
@click.option("--build/--no-build", default=True, help="make FBMatrix sau khi mount source")
@click.option("--down-first", is_flag=True, help="docker-compose down trước khi cài")
@click.option("--no-autostart", is_flag=True, help="Không cài systemd autostart")
@click.pass_context
def dev_fpp_bootstrap(
    ctx: click.Context,
    source: Path | None,
    compose_dir: str | None,
    http_port: int,
    build: bool,
    down_first: bool,
    no_autostart: bool,
) -> None:
    """Greenfield: upload FPP source → install Docker → build → khởi động trên target."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result(
                "dev.fpp.bootstrap",
                {"source": str(source), "http_port": http_port, "down_first": down_first},
            ),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Bootstrap FPP trên target (upload source + docker + build)?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.fpp.bootstrap"}, _json_flag(ctx))
        return
    try:
        output(
            fpp_mod.fpp_bootstrap(
                source=source,
                compose_dir=compose_dir,
                http_port=http_port,
                build=build,
                autostart=not no_autostart,
                down_first=down_first,
            ),
            _json_flag(ctx),
        )
    except (ValueError, FileNotFoundError) as exc:
        output({"error": str(exc)}, _json_flag(ctx))
        raise SystemExit(1) from exc


@dev_fpp_group.command("pull")
@click.option("--compose-dir", default=None)
@click.pass_context
def dev_fpp_pull(ctx: click.Context, compose_dir: str | None) -> None:
    """docker-compose pull."""
    output(fpp_mod.fpp_pull(compose_dir=compose_dir), _json_flag(ctx))


@dev_fpp_group.command("up")
@click.option("--compose-dir", default=None)
@click.pass_context
def dev_fpp_up(ctx: click.Context, compose_dir: str | None) -> None:
    """docker-compose up -d."""
    output(fpp_mod.fpp_up(compose_dir=compose_dir), _json_flag(ctx))


@dev_fpp_group.command("deploy")
@click.option("--source", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
@click.option("--file", "files", multiple=True, help="File trong FPP source (có thể lặp)")
@click.option("--compose-dir", default=None)
@click.option("--build/--no-build", default=True, help="make libfpp-co-FBMatrix.so trong container")
@click.option("--build-target", default="FBMatrix", show_default=True)
@click.option("--no-restart", is_flag=True, help="Không restart container sau deploy")
@click.pass_context
def dev_fpp_deploy(
    ctx: click.Context,
    source: Path | None,
    files: tuple[str, ...],
    compose_dir: str | None,
    build: bool,
    build_target: str,
    no_restart: bool,
) -> None:
    """Upload file từ FPP source local → container (+ build + restart)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result("dev.fpp.deploy", {"source": str(source), "files": list(files)}),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Deploy patch FPP lên container fpp-docker?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.fpp.deploy"}, _json_flag(ctx))
        return
    output(
        fpp_mod.fpp_deploy(
            source=source,
            files=list(files) if files else None,
            compose_dir=compose_dir,
            build=build,
            build_target=build_target,
            restart_container=not no_restart,
        ),
        _json_flag(ctx),
    )


@dev_fpp_group.command("build")
@click.option("--target", default="FBMatrix", show_default=True, type=click.Choice(["FBMatrix", "all"]))
@click.pass_context
def dev_fpp_build(ctx: click.Context, target: str) -> None:
    """Chạy make trong container (plugin FBMatrix hoặc all)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("dev.fpp.build", {"target": target}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        f"Build FPP target '{target}' trong container?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.fpp.build"}, _json_flag(ctx))
        return
    output(fpp_mod.fpp_build(target=target), _json_flag(ctx))


@dev_fpp_group.group("virtual-matrix")
def dev_fpp_vm_group() -> None:
    """VirtualMatrix trong co-other.json (fb0 flip / rotate)."""


@dev_fpp_vm_group.command("status")
@click.option("--compose-dir", default=None)
@click.pass_context
def dev_fpp_vm_status(ctx: click.Context, compose_dir: str | None) -> None:
    """Đọc invert, flipHorizontal, rotate, width, height."""
    output(fpp_mod.virtual_matrix_status(compose_dir=compose_dir), _json_flag(ctx))


@dev_fpp_vm_group.command("set")
@click.option("--compose-dir", default=None)
@click.option("--invert/--no-invert", default=None)
@click.option("--flip-horizontal/--no-flip-horizontal", default=None)
@click.option("--rotate", type=click.Choice(["0", "90", "180", "270"]), default=None)
@click.option("--width", type=int, default=None)
@click.option("--height", type=int, default=None)
@click.option("--device", default=None)
@click.option("--no-restart", is_flag=True)
@click.pass_context
def dev_fpp_vm_set(
    ctx: click.Context,
    compose_dir: str | None,
    invert: bool | None,
    flip_horizontal: bool | None,
    rotate: str | None,
    width: int | None,
    height: int | None,
    device: str | None,
    no_restart: bool,
) -> None:
    """Cập nhật co-other.json + sync vào container."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result(
                "dev.fpp.virtual-matrix.set",
                {
                    "invert": invert,
                    "flip_horizontal": flip_horizontal,
                    "rotate": rotate,
                    "width": width,
                    "height": height,
                },
            ),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Cập nhật Virtual Matrix (co-other.json) và restart FPP?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.fpp.virtual-matrix.set"}, _json_flag(ctx))
        return
    rot = int(rotate) if rotate is not None else None
    output(
        fpp_mod.virtual_matrix_set(
            compose_dir=compose_dir,
            invert=invert,
            flip_horizontal=flip_horizontal,
            rotate=rot,
            width=width,
            height=height,
            device=device,
            restart_container=not no_restart,
        ),
        _json_flag(ctx),
    )


@dev_group.group("host")
def host_group() -> None:
    """SSH tới máy chạy FPP (Orange Pi) — màn hình, rotation, autostart."""


@host_group.group("display")
def host_display_group() -> None:
    """Framebuffer / HDMI on the host (not FPP API)."""


@host_display_group.command("status")
@click.pass_context
def host_display_status(ctx: click.Context) -> None:
    """EDID, orientation, fb0 geometry (SSH)."""
    output(host_mod.display_status(), _json_flag(ctx))


@host_display_group.command("rotate")
@click.argument(
    "mode",
    type=click.Choice(
        ["landscape", "portrait", "portrait-right", "portrait-left", "inverted"],
        case_sensitive=False,
    ),
)
@click.pass_context
def host_display_rotate(ctx: click.Context, mode: str) -> None:
    """Rotate physical display via /sys/class/graphics/fb0/rotate (requires sudo on host)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("dev.host.display.rotate", {"mode": mode}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        f"Xoay màn hình host sang '{mode}'? (Orange Pi fb0)",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.host.display.rotate"}, _json_flag(ctx))
        return
    output(host_mod.display_rotate(mode), _json_flag(ctx))


@host_display_group.group("persist")
def host_display_persist_group() -> None:
    """Giữ rotation sau reboot (systemd trên Orange Pi)."""


@host_display_persist_group.command("status")
@click.pass_context
def host_display_persist_status(ctx: click.Context) -> None:
    """Trạng thái service fpp-fb-rotate."""
    output(host_mod.persist_status(), _json_flag(ctx))


@host_display_persist_group.command("install")
@click.argument(
    "mode",
    default="portrait-right",
    type=click.Choice(
        ["landscape", "portrait", "portrait-right", "portrait-left", "inverted"],
        case_sensitive=False,
    ),
)
@click.pass_context
def host_display_persist_install(ctx: click.Context, mode: str) -> None:
    """Cài systemd + script, bật portrait cố định sau reboot."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result("dev.host.display.persist.install", {"mode": mode}),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        f"Cài systemd giữ rotation '{mode}' sau reboot?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.host.display.persist.install"}, _json_flag(ctx))
        return
    output(host_mod.install_display_persist(mode), _json_flag(ctx))


@host_display_persist_group.command("remove")
@click.pass_context
def host_display_persist_remove(ctx: click.Context) -> None:
    """Gỡ systemd persist và về landscape."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("dev.host.display.persist.remove", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Gỡ persist rotation và về landscape?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.host.display.persist.remove"}, _json_flag(ctx))
        return
    output(host_mod.remove_display_persist(), _json_flag(ctx))


@host_group.group("fpp")
def host_fpp_group() -> None:
    """FPP trên Orange Pi host (docker-compose, autostart)."""


@host_fpp_group.group("autostart")
def host_fpp_autostart_group() -> None:
    """Tự khởi động FPP docker khi Orange Pi boot."""


@host_fpp_autostart_group.command("status")
@click.pass_context
def host_fpp_autostart_status(ctx: click.Context) -> None:
    """Trạng thái docker.service + fpp-docker.service + container."""
    output(host_mod.fpp_autostart_status(), _json_flag(ctx))


@host_fpp_autostart_group.command("install")
@click.option("--compose-dir", default=None, help="Thư mục docker-compose.yml trên host")
@click.pass_context
def host_fpp_autostart_install(ctx: click.Context, compose_dir: str | None) -> None:
    """Bật docker.service + systemd fpp-docker (docker-compose up -d khi boot)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(
            confirm_mod.dry_run_result("dev.host.fpp.autostart.install", {"compose_dir": compose_dir}),
            _json_flag(ctx),
        )
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Cài autostart FPP docker khi Orange Pi boot?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.host.fpp.autostart.install"}, _json_flag(ctx))
        return
    output(host_mod.install_fpp_autostart(compose_dir), _json_flag(ctx))


@host_fpp_autostart_group.command("remove")
@click.pass_context
def host_fpp_autostart_remove(ctx: click.Context) -> None:
    """Gỡ systemd fpp-docker (container restart:always vẫn giữ trong compose)."""
    if confirm_mod.is_dry_run(ctx.obj):
        output(confirm_mod.dry_run_result("dev.host.fpp.autostart.remove", {}), _json_flag(ctx))
        return
    if not confirm_mod.require_confirm(
        ctx.obj,
        "Gỡ autostart systemd fpp-docker?",
        as_json=_json_flag(ctx),
    ):
        output({"cancelled": True, "action": "dev.host.fpp.autostart.remove"}, _json_flag(ctx))
        return
    output(host_mod.remove_fpp_autostart(), _json_flag(ctx))


@cli.command("host", hidden=True)
@click.argument("subargs", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def host_legacy_forward(ctx: click.Context, subargs: tuple[str, ...]) -> None:
    """Chuyển tiếp `host …` → `dev host …` (tương thích script cũ)."""
    if not subargs:
        click.secho("Đã chuyển sang: cli-fpp dev host <lệnh>", fg="yellow", err=True)
        raise SystemExit(2)
    try:
        cli.main(["dev", "host", *subargs], standalone_mode=False, obj=ctx.obj)
    except SystemExit as exc:
        raise SystemExit(exc.code) from exc


@cli.command("repl", hidden=True)
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Interactive REPL (default when no subcommand given)."""
    from cli_fpp.utils.repl_skin import ReplSkin

    skin = ReplSkin("fpp", version=__version__)
    skin.print_banner()

    if not ctx.obj.get("skip_setup"):
        try:
            setup_data = target_setup_mod.run_setup(
                interactive=True,
                skip_add_prompt=False,
            )
            target_setup_mod.print_briefing(setup_data, skin=skin)
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            return

    try:
        skin.info(f"Target active: {ctx.obj.get('target') or '(default)'} — {_conn(ctx)}")
    except ValueError:
        skin.info("Chưa cấu hình FPP URL — dùng: target add <name> hoặc target setup")

    pt_session = skin.create_prompt_session()
    commands_dict = {
        "suggest <prompt>": "Đọc ý user → đề xuất CLI + web UI + confirm",
        "guide topics|show <topic>": "Hướng dẫn sử dụng",
        "ping": "Check connectivity",
        "player status|current": "Đang phát gì (index.php)",
        "system status|info|fppd|version|volume|restart|fppd-start|fppd-stop": "System / fppd",
        "playlist list [--playable]|get|play|stop|next|prev|pause": "Playlist control",
        "sequence pause|step|stop": "Sequence pause/step (index.php)",
        "media list|sequences|duration": "Media files",
        "effects list|running|start|stop": "Effects",
        "overlays models|running|stop": "Pixel overlays",
        "gpio list|get|set": "GPIO pins",
        "experience list|remember|catalog": "Kinh nghiệm theo device + FPP version",
        "dev doctor": "Kiểm tra target + gợi ý bootstrap",
        "dev target show|init": "Profile FPP URL + SSH (alias target add)",
        "dev fpp bootstrap|status|down|up": "Cài mới / vận hành Docker FPP",
        "dev fpp virtual-matrix status|set": "co-other.json — flip/rotate fb0",
        "dev host display status|rotate|persist": "SSH Orange Pi — xoay màn + systemd",
        "dev host fpp autostart status|install|remove": "SSH — FPP docker tự chạy khi boot",
        "api list|call|<tag> <cmd>": "Full REST API (253 ops)",
        "command list|help|run|presets|preset": "FPP commands",
        "schedule list|reload|extend|next": "Schedules",
        "config show|set": "CLI config",
        "--dry-run / --yes": "Xem trước / bỏ qua confirm",
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
        try:
            contrib_mod.capture_cli_error(exc, command_hint=" ".join(sys.argv))
        except Exception:
            pass
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except ValueError as exc:
        try:
            contrib_mod.capture_cli_error(exc, command_hint=" ".join(sys.argv))
        except Exception:
            pass
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()


# Register full OpenAPI wrap (253 operations) after cli group is defined.
from cli_fpp.cli_openapi import register_openapi  # noqa: E402

register_openapi(cli)
