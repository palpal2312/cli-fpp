"""Target briefing, interactive setup, and FPP version audit."""

from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

import click

from cli_fpp.core import dev_target
from cli_fpp.core import experiences as exp_mod
from cli_fpp.core import host_ssh
from cli_fpp.core import project
from cli_fpp.core import target_catalog
from cli_fpp.utils import fpp_backend

PromptFn = Callable[[str, str | None], str]


def _normalize_url(url: str) -> str:
    url = str(url or "").strip().rstrip("/")
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url


def _auth_for_profile(profile: dict[str, Any]) -> tuple[str, str] | None:
    user = str(profile.get("username", "")).strip()
    pwd = profile.get("password", "")
    return (user, pwd) if user else None


def _guess_ssh_host(fpp_url: str) -> str:
    try:
        return urlparse(_normalize_url(fpp_url)).hostname or ""
    except ValueError:
        return ""


def parse_fpp_version(data: Any) -> str | None:
    if data is None:
        return None
    if isinstance(data, str):
        text = data.strip()
        return text or None
    if isinstance(data, dict):
        for key in ("version", "Version", "fppd", "FPPD", "ver"):
            if data.get(key):
                return str(data[key]).strip()
        if len(data) == 1:
            return str(next(iter(data.values()))).strip()
    return str(data).strip() or None


def _parse_ssh_fpp_version(output: str) -> str | None:
    text = (output or "").strip()
    if not text:
        return None
    match = re.search(r"FPP\s+v?([\d.]+(?:-[\w.]+)?)", text, re.I)
    if match:
        return match.group(1)
    first = text.splitlines()[0].strip()
    return first or None


def check_fpp_version(
    name: str,
    *,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ping FPP HTTP API (and SSH docker fallback) for version info."""
    raw = project.load_raw_config()
    if profile is None:
        try:
            profile = project.get_target_profile(name, raw=raw)
        except KeyError:
            return {
                "name": name,
                "ok": False,
                "reachable": False,
                "version": None,
                "source": None,
                "error": f"Unknown target: {name}",
            }

    base_url = _normalize_url(str(profile.get("base_url", "")))
    missing = dev_target._missing_keys(profile, dev_target.CLIENT_REQUIRED_KEYS)
    result: dict[str, Any] = {
        "name": name,
        "label": profile.get("label") or "",
        "base_url": base_url or None,
        "ok": False,
        "reachable": False,
        "version": None,
        "source": None,
        "error": None,
    }
    if missing:
        result["error"] = f"Thiếu cấu hình client: {', '.join(missing)}"
        result.update(target_catalog.device_type_info(profile))
        return result

    auth = _auth_for_profile(profile)
    errors: list[str] = []

    for endpoint, source in (
        ("/api/fppd/version", "api/fppd/version"),
        ("/api/fppd/status", "api/fppd/status"),
        ("/api/system/info", "api/system/info"),
    ):
        try:
            data = fpp_backend.api_get(endpoint, base_url=base_url, auth=auth)
            version = parse_fpp_version(data)
            if version:
                result.update(
                    {
                        "ok": True,
                        "reachable": True,
                        "version": version,
                        "source": source,
                        "error": None,
                    }
                )
                result.update(target_catalog.apply_check_classifications(result, profile))
                return result
            result["reachable"] = True
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    ssh_host = str(profile.get("ssh_host", "")).strip() or _guess_ssh_host(base_url)
    ssh_password = profile.get("ssh_password", "")
    if ssh_host and ssh_password:
        try:
            conf = host_ssh.SSHConfig(
                host=ssh_host,
                user=str(profile.get("ssh_user") or "orangepi"),
                password=str(ssh_password),
                port=int(profile.get("ssh_port") or 22),
            )
            out = host_ssh.run_ssh(
                "docker exec fpp-docker fpp -V 2>/dev/null || docker exec fpp-docker /opt/fpp/src/fpp -V 2>/dev/null",
                conf=conf,
            )
            version = _parse_ssh_fpp_version(out)
            if version:
                result.update(
                    {
                        "ok": True,
                        "reachable": True,
                        "version": version,
                        "source": "ssh/docker fpp -V",
                        "error": None,
                    }
                )
                result.update(target_catalog.apply_check_classifications(result, profile))
                return result
        except Exception as exc:
            errors.append(f"ssh: {exc}")

    if result["reachable"]:
        result["error"] = "Kết nối được nhưng không đọc được phiên bản FPP"
    elif errors:
        result["error"] = errors[0]
    else:
        result["error"] = "Không kết nối được FPP"
    result.update(target_catalog.apply_check_classifications(result, profile))
    return result


def audit_all_targets(*, persist: bool = True) -> dict[str, Any]:
    """Check FPP version on every saved target; lưu player version + phân loại."""
    listing = dev_target.list_targets(mask_secrets=True)
    checks: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for item in listing["targets"]:
        name = item["name"]
        profile = project.get_target_profile(name)
        check = check_fpp_version(name, profile=profile)
        if persist and check.get("version"):
            target_catalog.persist_player_version(name, check)
        checks.append(check)
        records.append(
            target_catalog.enrich_target_record(
                name,
                project.get_target_profile(name),
            )
        )

    ok_count = sum(1 for c in checks if c.get("ok"))
    experience_hints = exp_mod.experiences_for_suggest(limit_per_layer=3)
    audit = {
        "target_count": listing["count"],
        "default_target": listing.get("default_target"),
        "active_target": listing.get("active_target"),
        "reachable_count": sum(1 for c in checks if c.get("reachable")),
        "version_ok_count": ok_count,
        "checks": checks,
        "by_device_type": target_catalog.group_by_device_type(records),
        "by_player_version": target_catalog.group_by_player_version(records),
        "experience_hints": experience_hints,
    }
    try:
        from cli_fpp.core import experience_contrib as contrib_mod

        audit["contrib_captured"] = len(contrib_mod.capture_from_audit(audit))
        st = contrib_mod.queue_status()
        audit["contrib"] = {"pending": st["pending"], "enabled": st["enabled"]}
        raw = project.load_raw_config()
        if raw.get("contrib_prompt_after_audit") and st["pending"] > 0:
            audit["contrib_prompt"] = "cli-fpp experience contribute submit --github"
    except Exception:
        pass
    return audit


def target_briefing() -> dict[str, Any]:
    """Summary for startup: how many targets are managed."""
    listing = dev_target.list_targets(mask_secrets=True)
    names = [t["name"] for t in listing["targets"]]
    return {
        "target_count": listing["count"],
        "default_target": listing.get("default_target"),
        "active_target": listing.get("active_target"),
        "target_names": names,
        "targets": listing["targets"],
    }


def _default_prompt(label: str, default: str | None = None) -> str:
    if default:
        return click.prompt(label, default=default, show_default=True).strip()
    return click.prompt(label).strip()


def _collect_target_fields(
    name: str,
    *,
    prompt: PromptFn | None = None,
    defaults: dict[str, str] | None = None,
) -> dict[str, str]:
    defaults = defaults or {}
    ask = prompt or _default_prompt
    fpp_url = ask("FPP URL", defaults.get("fpp_url") or "http://192.168.1.39:81")
    fpp_user = ask("FPP user", defaults.get("fpp_user") or "admin")
    fpp_password = ask("FPP password", defaults.get("fpp_password"))
    ssh_host = ask("SSH host", defaults.get("ssh_host") or _guess_ssh_host(fpp_url))
    ssh_user = ask("SSH user", defaults.get("ssh_user") or "orangepi")
    ssh_password = ask("SSH password", defaults.get("ssh_password"))
    label = ask("Nhãn (tuỳ chọn, Enter bỏ qua)", defaults.get("label") or "") or ""
    device_default = defaults.get("device_type") or "orangepi"
    device_type = ask(
        "Loại thiết bị (orangepi/raspberrypi/bbb/x86/generic)",
        device_default,
    )
    return {
        "name": name,
        "fpp_url": fpp_url,
        "fpp_user": fpp_user,
        "fpp_password": fpp_password,
        "ssh_host": ssh_host,
        "ssh_user": ssh_user,
        "ssh_password": ssh_password,
        "label": label,
        "device_type": device_type,
    }


def _save_collected(fields: dict[str, str], *, make_default: bool) -> dict[str, Any]:
    return dev_target.add_target(
        fields["name"],
        base_url=fields["fpp_url"],
        username=fields["fpp_user"],
        password=fields["fpp_password"],
        ssh_host=fields["ssh_host"],
        ssh_user=fields["ssh_user"],
        ssh_password=fields["ssh_password"],
        label=fields.get("label") or None,
        device_type=fields.get("device_type") or None,
        make_default=make_default,
    )


def _interactive_add_batch(
    count: int,
    *,
    existing_count: int,
    prompt: PromptFn | None = None,
) -> list[dict[str, Any]]:
    added: list[dict[str, Any]] = []
    for i in range(count):
        default_name = f"target-{existing_count + i + 1}"
        ask = prompt or _default_prompt
        name = ask(f"Tên target #{i + 1}", default_name)
        if not name:
            continue
        fields = _collect_target_fields(name, prompt=prompt)
        make_default = existing_count == 0 and i == 0
        added.append(_save_collected(fields, make_default=make_default))
    return added


def _interactive_add_one_by_one(
    *,
    existing_count: int,
    prompt: PromptFn | None = None,
) -> list[dict[str, Any]]:
    added: list[dict[str, Any]] = []
    index = existing_count
    ask = prompt or _default_prompt
    while True:
        name = ask("Tên target (Enter để dừng)", "")
        if not name:
            break
        index += 1
        fields = _collect_target_fields(name, prompt=prompt)
        make_default = not project.list_target_names() and len(added) == 0
        added.append(_save_collected(fields, make_default=make_default))
        more = ask("Thêm target nữa? [y/N]", "n").lower()
        if more not in ("y", "yes", "có", "co"):
            break
    return added


def run_setup(
    *,
    interactive: bool = True,
    add_mode: str | None = None,
    add_count: int | None = None,
    skip_add_prompt: bool = False,
) -> dict[str, Any]:
    """
    Startup flow:
    1. Announce managed target count
    2. Optionally add targets (batch count or one-by-one)
    3. Auto-check FPP version on all targets
    """
    briefing = target_briefing()
    added: list[dict[str, Any]] = []

    if interactive and not skip_add_prompt:
        if briefing["target_count"] == 0:
            click.echo("Chưa có target nào — hãy thêm ít nhất một thiết bị FPP.")
        else:
            click.echo(
                f"Đang quản lý {briefing['target_count']} target-device: "
                + ", ".join(briefing["target_names"])
            )

        if add_mode is None:
            choice = click.prompt(
                "Thêm target? [1=theo số lượng, 2=từng cái, Enter=bỏ qua]",
                default="",
                show_default=False,
            ).strip()
            if choice == "1":
                add_mode = "batch"
            elif choice == "2":
                add_mode = "one"

        if add_mode == "batch":
            count = add_count
            if count is None:
                count = click.prompt("Số target cần thêm", type=int, default=1)
            added = _interactive_add_batch(
                max(1, int(count)),
                existing_count=briefing["target_count"],
            )
        elif add_mode == "one":
            added = _interactive_add_one_by_one(existing_count=briefing["target_count"])

    briefing = target_briefing()
    audit = audit_all_targets()
    return {
        "briefing": briefing,
        "added": added,
        "audit": audit,
    }


def format_briefing_text(data: dict[str, Any]) -> str:
    lines: list[str] = []
    briefing = data.get("briefing") or target_briefing()
    count = briefing.get("target_count", 0)
    if count == 0:
        lines.append("Chưa quản lý target-device nào.")
    else:
        names = ", ".join(briefing.get("target_names") or [])
        lines.append(f"Đang quản lý {count} target-device: {names}")

    audit = data.get("audit") or {}
    checks = audit.get("checks") or []
    if checks:
        lines.append("")
        lines.append("Kiểm tra Player (FPP version):")
        for item in checks:
            name = item.get("name", "?")
            device = item.get("device_label") or item.get("device_type") or "?"
            version = item.get("player_version") or item.get("version") or "—"
            group = item.get("player_group") or "unknown"
            status = "OK" if item.get("ok") else "LỖI"
            err = f" ({item['error']})" if item.get("error") and not item.get("ok") else ""
            lines.append(f"  • {name} [{device}] FPP {version} ({group}) [{status}]{err}")

    by_device = audit.get("by_device_type", {}).get("groups") or []
    if by_device:
        lines.append("")
        lines.append("Theo loại Target (thiết bị):")
        for grp in by_device:
            lines.append(
                f"  • {grp['device_label']}: {grp['count']} — {', '.join(grp['targets'])}"
            )

    by_player = audit.get("by_player_version", {}).get("groups") or []
    if by_player:
        lines.append("")
        lines.append("Theo Player (FPP version):")
        for grp in by_player:
            vers = ", ".join(grp.get("versions") or []) or "—"
            lines.append(
                f"  • {grp['player_group']}: {grp['count']} — {', '.join(grp['targets'])} ({vers})"
            )

    hints = audit.get("experience_hints") or {}
    if hints:
        lines.append("")
        lines.append(hints.get("priority_hint") or exp_mod.PRIORITY_HINT)
        for layer_key, label in (
            ("global", "Chung (mọi target)"),
            ("device_specific", "Riêng Target (thiết bị)"),
            ("player_specific", "Riêng Player (FPP version)"),
        ):
            items = hints.get(layer_key) or []
            if not items:
                continue
            lines.append(f"{label}:")
            for hint in items[:3]:
                lines.append(f"  • {hint.get('title')} — {hint.get('match_reason', hint.get('applies_to', ''))}")
    return "\n".join(lines)


def print_briefing(data: dict[str, Any], *, skin: Any | None = None) -> None:
    text = format_briefing_text(data)
    if skin is not None:
        skin.info(text)
        return
    click.echo(text)
