"""Target device profiles, multi-target registry, and health checks."""

from __future__ import annotations

from typing import Any

from cli_fpp.core import host_ssh
from cli_fpp.core import project
from cli_fpp.core import target_catalog
from cli_fpp.utils import fpp_backend

REQUIRED_KEYS = ("base_url", "username", "password", "ssh_host", "ssh_password")
CLIENT_REQUIRED_KEYS = ("base_url", "username", "password")


def _missing_keys(profile: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for key in keys:
        if not str(profile.get(key, "")).strip():
            missing.append(key)
    return missing


def _mask_profile(profile: dict[str, Any], *, mask_secrets: bool) -> dict[str, Any]:
    out = dict(profile)
    if mask_secrets and out.get("password"):
        out["password"] = "****"
    if mask_secrets and out.get("ssh_password"):
        out["ssh_password"] = "****"
    out["ssh_port"] = int(out.get("ssh_port") or 22)
    return out


def list_targets(*, mask_secrets: bool = True) -> dict[str, Any]:
    """All saved targets + default marker."""
    raw = project.load_raw_config()
    default = str(raw.get("default_target") or "").strip()
    active = project.get_active_target_name(raw=raw)
    names = project.list_target_names(raw=raw)
    items: list[dict[str, Any]] = []
    for name in names:
        try:
            profile = project.get_target_profile(name, raw=raw)
        except KeyError:
            continue
        items.append(
            {
                "name": name,
                "default": name == default,
                "active": name == active,
                "complete_client": not _missing_keys(profile, CLIENT_REQUIRED_KEYS),
                "complete_dev": not _missing_keys(profile, REQUIRED_KEYS),
                "profile": _mask_profile(profile, mask_secrets=mask_secrets),
                **target_catalog.device_type_info(profile),
                **target_catalog.player_info_from_profile(profile),
            }
        )
    return {
        "default_target": default or None,
        "active_target": active,
        "count": len(items),
        "targets": items,
        "by_device_type": target_catalog.group_by_device_type(
            [
                {
                    "name": i["name"],
                    "device_type": i["device_type"],
                    **target_catalog.player_info_from_profile(
                        project.get_target_profile(i["name"], raw=raw)
                    ),
                }
                for i in items
            ]
        ),
        "by_player_version": target_catalog.group_by_player_version(
            [
                {
                    "name": i["name"],
                    **target_catalog.player_info_from_profile(
                        project.get_target_profile(i["name"], raw=raw)
                    ),
                }
                for i in items
            ]
        ),
    }


def target_profile(*, name: str | None = None, mask_secrets: bool = True) -> dict[str, Any]:
    """One target profile (active/default if name omitted)."""
    raw = project.load_raw_config()
    resolved = name or project.get_active_target_name(raw=raw) or raw.get("default_target")
    if not resolved:
        cfg = project.load_config()
        profile = _mask_profile(
            {k: cfg.get(k, "") for k in project.TARGET_PROFILE_KEYS},
            mask_secrets=mask_secrets,
        )
        profile["name"] = None
        profile["missing"] = _missing_keys(profile, REQUIRED_KEYS)
        profile["missing_client"] = _missing_keys(profile, CLIENT_REQUIRED_KEYS)
        profile["complete"] = not profile["missing"]
        profile["complete_client"] = not profile["missing_client"]
        return profile

    try:
        profile = project.get_target_profile(resolved, raw=raw)
    except KeyError:
        out = _mask_profile({}, mask_secrets=mask_secrets)
        out["name"] = resolved
        out["missing"] = list(REQUIRED_KEYS)
        out["missing_client"] = list(CLIENT_REQUIRED_KEYS)
        out["complete"] = False
        out["complete_client"] = False
        out["error"] = f"Unknown target: {resolved}"
        return out
    out = _mask_profile(profile, mask_secrets=mask_secrets)
    out["name"] = resolved
    out["default"] = resolved == raw.get("default_target")
    out["missing"] = _missing_keys(profile, REQUIRED_KEYS)
    out["missing_client"] = _missing_keys(profile, CLIENT_REQUIRED_KEYS)
    out["complete"] = not out["missing"]
    out["complete_client"] = not out["missing_client"]
    return out


def save_target(
    *,
    name: str | None = None,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    ssh_host: str | None = None,
    ssh_user: str | None = None,
    ssh_password: str | None = None,
    ssh_port: int | None = None,
    label: str | None = None,
    device_type: str | None = None,
    make_default: bool = False,
) -> dict[str, Any]:
    raw = project.load_raw_config()
    resolved = name or project.get_active_target_name(raw=raw)
    if not resolved:
        resolved = "default"
    fields: dict[str, Any] = {}
    if base_url is not None:
        fields["base_url"] = base_url
    if username is not None:
        fields["username"] = username
    if password is not None:
        fields["password"] = password
    if ssh_host is not None:
        fields["ssh_host"] = ssh_host
    if ssh_user is not None:
        fields["ssh_user"] = ssh_user
    if ssh_password is not None:
        fields["ssh_password"] = ssh_password
    if ssh_port is not None:
        fields["ssh_port"] = ssh_port
    if label is not None:
        fields["label"] = label
    if device_type is not None:
        fields["device_type"] = target_catalog.normalize_device_type(device_type)
    result = project.upsert_target(resolved, fields, make_default=make_default)
    return {"saved": result["saved"], "name": resolved, "profile": target_profile(name=resolved)}


def add_target(
    name: str,
    *,
    base_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    ssh_host: str | None = None,
    ssh_user: str | None = None,
    ssh_password: str | None = None,
    ssh_port: int | None = None,
    label: str | None = None,
    device_type: str | None = None,
    make_default: bool = False,
) -> dict[str, Any]:
    if not any([base_url, username, password, ssh_host, ssh_password]):
        raise ValueError("Cần ít nhất base_url hoặc ssh_host hoặc credentials")
    return save_target(
        name=name,
        base_url=base_url,
        username=username,
        password=password,
        ssh_host=ssh_host,
        ssh_user=ssh_user,
        ssh_password=ssh_password,
        ssh_port=ssh_port,
        label=label,
        device_type=device_type,
        make_default=make_default,
    )


def use_target(name: str) -> dict[str, Any]:
    result = project.set_default_target(name)
    project.set_active_target(name)
    return {
        **result,
        "profile": target_profile(name=name),
        "hint": f"Dùng: cli-fpp -t {name} <lệnh>  hoặc export FPP_TARGET={name}",
    }


def remove_target(name: str) -> dict[str, Any]:
    return project.remove_target(name)


def dev_doctor(
    *,
    compose_dir: str | None = None,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    """Kiểm tra config + SSH + Docker + FPP HTTP trên target."""
    profile = target_profile()
    result: dict[str, Any] = {
        "target": profile.get("name"),
        "profile": profile,
        "checks": {},
        "ready": False,
        "fpp_installed": False,
        "next_steps": [],
    }

    if profile.get("missing_client"):
        result["checks"]["config"] = {"ok": False, "missing": profile["missing_client"]}
        result["next_steps"] = [
            "cli-fpp target add <name> --fpp-url http://HOST:81 --fpp-user admin --fpp-password ***",
            "cli-fpp target use <name>",
        ]
        return result

    result["checks"]["config"] = {"ok": True}

    if profile.get("missing"):
        result["checks"]["ssh_config"] = {"ok": False, "missing": profile["missing"]}
        result["next_steps"].append(
            "cli-fpp target add <name> --ssh-host HOST --ssh-password ***  # cho dev/SSH"
        )
        return result

    try:
        conf = conf or host_ssh.get_ssh_config()
    except ValueError as exc:
        result["checks"]["ssh_config"] = {"ok": False, "error": str(exc)}
        return result

    ssh_ping = host_ssh.run_ssh("echo ok", conf=conf).strip()
    result["checks"]["ssh"] = {"ok": ssh_ping == "ok", "host": conf.host}

    docker_ver = host_ssh.run_ssh("docker --version 2>/dev/null", conf=conf).strip()
    compose_ver = host_ssh.run_ssh("docker-compose --version 2>/dev/null", conf=conf).strip()
    result["checks"]["docker"] = {
        "ok": bool(docker_ver),
        "docker": docker_ver or None,
        "compose": compose_ver or None,
    }

    from cli_fpp.core import fpp_docker

    fpp = fpp_docker.fpp_status(compose_dir=compose_dir, conf=conf)
    container_running = fpp.get("container", {}).get("status") == "running"
    has_compose = bool(fpp.get("has_compose"))
    result["checks"]["fpp_docker"] = {
        "ok": container_running,
        "has_compose": has_compose,
        "has_media": fpp.get("has_media"),
        "image_pulled": fpp.get("image_pulled"),
        "container": fpp.get("container"),
        "http": fpp.get("fpp_http"),
    }
    result["fpp_installed"] = has_compose and container_running
    result["fpp_status"] = fpp

    try:
        ping = fpp_backend.ping(base_url=project.get_connection())
        result["checks"]["fpp_api"] = {"ok": True, "ping": ping}
    except Exception as exc:
        result["checks"]["fpp_api"] = {"ok": False, "error": str(exc)}

    ok_ssh = result["checks"]["ssh"]["ok"]
    ok_docker = result["checks"]["docker"]["ok"]
    ok_api = result["checks"]["fpp_api"]["ok"]
    result["ready"] = ok_ssh and ok_docker and result["fpp_installed"] and ok_api

    target_flag = f" -t {profile['name']}" if profile.get("name") else ""
    if not result["fpp_installed"]:
        result["next_steps"].append(
            f"cli-fpp{target_flag} --json --yes dev fpp bootstrap --source <path-to-fpp>"
        )
    elif not ok_api:
        result["next_steps"].append(f"cli-fpp{target_flag} dev fpp up  # hoặc kiểm tra port / auth")
    elif result["ready"]:
        result["next_steps"].append(
            f"Target sẵn sàng — cli-fpp{target_flag} media upload / playlist play"
        )

    return result
