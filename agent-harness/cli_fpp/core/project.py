"""Configuration and connection management for cli-fpp."""

from __future__ import annotations

import contextvars
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".cli-fpp"
CONFIG_FILE = CONFIG_DIR / "config.json"

TARGET_PROFILE_KEYS = (
    "base_url",
    "username",
    "password",
    "ssh_host",
    "ssh_user",
    "ssh_password",
    "ssh_port",
    "label",
    "compose_dir",
    "device_type",
    "player_version",
    "player_version_source",
    "player_version_checked_at",
)

DEFAULTS: dict[str, Any] = {
    "base_url": "http://fpp.local",
    "username": "",
    "password": "",
    "ssh_host": "",
    "ssh_user": "orangepi",
    "ssh_password": "",
    "ssh_port": 22,
    "default_target": "",
    "targets": {},
    "contrib_enabled": True,
    "contrib_prompt_after_audit": False,
}

_ACTIVE_TARGET: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "fpp_active_target", default=None
)

_TARGET_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9._-]{0,63}$")


def validate_target_name(name: str) -> str:
    name = name.strip()
    if not name or not _TARGET_NAME_RE.match(name):
        raise ValueError(
            "Target name must start with a letter and use only letters, digits, '.', '-', '_'."
        )
    return name


def set_active_target(name: str | None) -> None:
    """Set target for current CLI invocation (also respects FPP_TARGET env)."""
    _ACTIVE_TARGET.set(validate_target_name(name) if name else None)


def get_active_target_name(*, raw: dict[str, Any] | None = None) -> str | None:
    """Resolve active target: CLI context → env → default_target in config."""
    ctx = _ACTIVE_TARGET.get()
    if ctx:
        return ctx
    if env := os.environ.get("FPP_TARGET", "").strip():
        return env
    raw = raw if raw is not None else load_raw_config()
    default = str(raw.get("default_target") or "").strip()
    return default or None


def _profile_from_flat(cfg: dict[str, Any]) -> dict[str, Any]:
    return {k: cfg[k] for k in TARGET_PROFILE_KEYS if k in cfg and cfg[k] not in (None, "")}


def _migrate_flat_to_targets(cfg: dict[str, Any]) -> dict[str, Any]:
    """One-time shape: flat keys → targets.default."""
    if cfg.get("targets"):
        return cfg
    profile = _profile_from_flat(cfg)
    if profile:
        cfg = deepcopy(cfg)
        cfg.setdefault("targets", {})["default"] = profile
        cfg.setdefault("default_target", "default")
    return cfg


def load_raw_config() -> dict[str, Any]:
    """Load config file without merging active target."""
    cfg: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg = loaded
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    return _migrate_flat_to_targets(cfg)


def save_raw_config(cfg: dict[str, Any]) -> Path:
    """Persist config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(CONFIG_DIR), 0o700)
    except OSError:
        pass
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(str(CONFIG_FILE), 0o600)
    except OSError:
        pass
    return CONFIG_FILE


def save_config(cfg: dict[str, Any]) -> Path:
    """Backward-compatible save — strips runtime-only keys."""
    clean = deepcopy(cfg)
    clean.pop("_target", None)
    return save_raw_config(clean)


def set_global_flag(key: str, value: Any) -> dict[str, Any]:
    """Set top-level config flag (e.g. contrib_enabled)."""
    if key not in DEFAULTS:
        raise ValueError(f"Unknown global key: {key}")
    raw = load_raw_config()
    if key == "contrib_enabled" or key == "contrib_prompt_after_audit":
        if isinstance(value, bool):
            parsed = value
        else:
            parsed = str(value).strip().lower() in ("1", "true", "yes", "on")
    else:
        parsed = value
    raw[key] = parsed
    path = save_raw_config(raw)
    return {"saved": str(path), key: parsed}


def list_target_names(*, raw: dict[str, Any] | None = None) -> list[str]:
    raw = raw if raw is not None else load_raw_config()
    names = sorted((raw.get("targets") or {}).keys())
    if not names:
        profile = _profile_from_flat(raw)
        if profile:
            return ["default"]
    return names


def get_target_profile(name: str, *, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = raw if raw is not None else load_raw_config()
    name = validate_target_name(name)
    targets = raw.get("targets") or {}
    if name in targets:
        return dict(targets[name])
    if name == "default":
        flat = _profile_from_flat(raw)
        if flat:
            return flat
    raise KeyError(f"Unknown target: {name}")


def effective_config(
    raw: dict[str, Any],
    target_name: str | None,
) -> dict[str, Any]:
    """Merge defaults + legacy flat keys + named target profile."""
    cfg = dict(DEFAULTS)
    for key in TARGET_PROFILE_KEYS:
        if key in raw and raw[key] not in (None, ""):
            cfg[key] = raw[key]

    targets = raw.get("targets") or {}
    chosen = target_name
    if chosen and chosen in targets:
        cfg.update(targets[chosen])
        cfg["_target"] = chosen
    elif targets and raw.get("default_target") in targets:
        chosen = raw["default_target"]
        cfg.update(targets[chosen])
        cfg["_target"] = chosen
    elif chosen == "default" and _profile_from_flat(raw):
        cfg["_target"] = "default"

    if url := os.environ.get("FPP_BASE_URL"):
        cfg["base_url"] = url
    if user := os.environ.get("FPP_USER"):
        cfg["username"] = user
    if password := os.environ.get("FPP_PASSWORD"):
        cfg["password"] = password
    if ssh_host := os.environ.get("FPP_SSH_HOST"):
        cfg["ssh_host"] = ssh_host
    if ssh_user := os.environ.get("FPP_SSH_USER"):
        cfg["ssh_user"] = ssh_user
    if ssh_password := os.environ.get("FPP_SSH_PASSWORD"):
        cfg["ssh_password"] = ssh_password
    return cfg


def load_config() -> dict[str, Any]:
    """Load config with active target merged (for API/SSH calls)."""
    raw = load_raw_config()
    name = get_active_target_name(raw=raw)
    return effective_config(raw, name)


def upsert_target(
    name: str,
    profile: dict[str, Any],
    *,
    make_default: bool = False,
) -> dict[str, Any]:
    """Add or update a named target profile."""
    name = validate_target_name(name)
    raw = load_raw_config()
    targets = dict(raw.get("targets") or {})
    merged = dict(targets.get(name) or {})
    for key, value in profile.items():
        if key in TARGET_PROFILE_KEYS and value is not None:
            if key == "base_url" and value:
                merged[key] = str(value).rstrip("/")
            elif key == "ssh_port":
                merged[key] = int(value)
            else:
                merged[key] = value
    targets[name] = merged
    raw["targets"] = targets
    if make_default or not raw.get("default_target"):
        raw["default_target"] = name
    if raw.get("default_target") == name:
        for key, value in merged.items():
            raw[key] = value
    path = save_raw_config(raw)
    return {"saved": str(path), "name": name, "profile": merged}


def remove_target(name: str) -> dict[str, Any]:
    name = validate_target_name(name)
    raw = load_raw_config()
    targets = dict(raw.get("targets") or {})
    if name not in targets:
        raise KeyError(f"Unknown target: {name}")
    del targets[name]
    raw["targets"] = targets
    if raw.get("default_target") == name:
        raw["default_target"] = next(iter(sorted(targets)), "")
        if raw["default_target"]:
            for key, value in targets[raw["default_target"]].items():
                raw[key] = value
        else:
            for key in TARGET_PROFILE_KEYS:
                raw.pop(key, None)
    path = save_raw_config(raw)
    return {"removed": name, "default_target": raw.get("default_target", ""), "saved": str(path)}


def set_default_target(name: str) -> dict[str, Any]:
    name = validate_target_name(name)
    raw = load_raw_config()
    targets = raw.get("targets") or {}
    if name not in targets and not (name == "default" and _profile_from_flat(raw)):
        raise KeyError(f"Unknown target: {name}")
    raw["default_target"] = name
    if name in targets:
        for key, value in targets[name].items():
            raw[key] = value
    path = save_raw_config(raw)
    return {"default_target": name, "saved": str(path)}


def set_target_field(name: str | None, key: str, value: Any) -> dict[str, Any]:
    """Update one profile field on a target (or active/default)."""
    if key not in TARGET_PROFILE_KEYS:
        raise ValueError(f"Unknown profile key: {key}")
    raw = load_raw_config()
    name = validate_target_name(name or get_active_target_name(raw=raw) or "default")
    targets = dict(raw.get("targets") or {})
    if name not in targets:
        targets[name] = {}
    if key == "base_url":
        value = str(value).rstrip("/")
    if key == "ssh_port":
        value = int(value)
    targets[name][key] = value
    raw["targets"] = targets
    raw.setdefault("default_target", name)
    if raw.get("default_target") == name:
        raw[key] = value
    path = save_raw_config(raw)
    return {"saved": str(path), "target": name, key: value}


def get_connection(base_url: str | None = None) -> str:
    """Resolve FPP base URL from args, env, or config file."""
    cfg = load_config()
    url = (base_url or cfg.get("base_url") or "").strip()
    if not url:
        raise ValueError(
            "FPP base URL not configured. Use --url, --target, FPP_BASE_URL, "
            "or: cli-fpp target add <name> --fpp-url <url>"
        )
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url.rstrip("/")


def get_auth(
    username: str | None = None,
    password: str | None = None,
) -> tuple[str, str] | None:
    """Resolve HTTP Basic Auth from args, env, or config file."""
    cfg = load_config()
    user = (username or cfg.get("username") or "").strip()
    pwd = password if password is not None else cfg.get("password", "")
    if user:
        return (user, pwd)
    return None
