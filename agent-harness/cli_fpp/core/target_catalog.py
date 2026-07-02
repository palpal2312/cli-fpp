"""Target (device) and Player (FPP) classification."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from cli_fpp.core import dev_target
from cli_fpp.core import project

DEVICE_TYPES: dict[str, dict[str, str]] = {
    "orangepi": {
        "label": "Orange Pi",
        "default_ssh_user": "orangepi",
        "description": "Orange Pi board (RK356x, …) chạy FPP Docker",
    },
    "raspberrypi": {
        "label": "Raspberry Pi",
        "default_ssh_user": "pi",
        "description": "Raspberry Pi chạy FPP",
    },
    "bbb": {
        "label": "BeagleBone Black",
        "default_ssh_user": "debian",
        "description": "BeagleBone Black / Green",
    },
    "x86": {
        "label": "x86 / Mini PC",
        "default_ssh_user": "root",
        "description": "PC / NUC chạy Linux + FPP",
    },
    "generic": {
        "label": "Generic Linux",
        "default_ssh_user": "root",
        "description": "Thiết bị Linux khác",
    },
}

DEFAULT_DEVICE_TYPE = "orangepi"

_VERSION_RE = re.compile(
    r"^(?:FPP\s+)?v?(?P<major>\d+)(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?"
    r"(?:[-_](?P<suffix>[\w.]+))?$",
    re.I,
)


def list_device_types() -> list[dict[str, str]]:
    return [
        {"id": key, **meta}
        for key, meta in DEVICE_TYPES.items()
    ]


def normalize_device_type(value: str | None) -> str:
    if not value:
        return DEFAULT_DEVICE_TYPE
    key = str(value).strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    aliases = {
        "orangepi": "orangepi",
        "orange": "orangepi",
        "opi": "orangepi",
        "raspberrypi": "raspberrypi",
        "rpi": "raspberrypi",
        "raspi": "raspberrypi",
        "pi": "raspberrypi",
        "bbb": "bbb",
        "beaglebone": "bbb",
        "beagleboneblack": "bbb",
        "x86": "x86",
        "pc": "x86",
        "minipc": "x86",
        "generic": "generic",
        "other": "generic",
    }
    resolved = aliases.get(key, key)
    if resolved not in DEVICE_TYPES:
        raise ValueError(
            f"Unknown device_type: {value}. "
            f"Choices: {', '.join(DEVICE_TYPES)}"
        )
    return resolved


def infer_device_type(profile: dict[str, Any]) -> str:
    explicit = str(profile.get("device_type") or "").strip()
    if explicit:
        try:
            return normalize_device_type(explicit)
        except ValueError:
            pass
    ssh_user = str(profile.get("ssh_user") or "").strip().lower()
    for device_id, meta in DEVICE_TYPES.items():
        if ssh_user == meta["default_ssh_user"]:
            return device_id
    return DEFAULT_DEVICE_TYPE


def device_type_info(profile: dict[str, Any]) -> dict[str, str]:
    device_id = infer_device_type(profile)
    meta = DEVICE_TYPES[device_id]
    return {
        "device_type": device_id,
        "device_label": meta["label"],
        "device_description": meta["description"],
    }


def classify_player_version(version: str | None) -> dict[str, Any]:
    """Phân loại Player (FPP) theo version string."""
    raw = (version or "").strip()
    if not raw:
        return {
            "player_version": None,
            "player_major": None,
            "player_minor": None,
            "player_line": "unknown",
            "player_channel": "unknown",
            "player_group": "unknown",
        }

    channel = "stable"
    lower = raw.lower()
    if "beta" in lower:
        channel = "beta"
    elif "alpha" in lower or "rc" in lower:
        channel = "pre-release"
    elif "master" in lower or "git" in lower:
        channel = "dev"

    match = _VERSION_RE.match(raw.split()[0] if " " in raw else raw)
    if not match:
        return {
            "player_version": raw,
            "player_major": None,
            "player_minor": None,
            "player_line": "other",
            "player_channel": channel,
            "player_group": f"other ({channel})",
        }

    major = int(match.group("major"))
    minor = int(match.group("minor") or 0)
    patch = int(match.group("patch") or 0)
    line = f"{major}.x"
    group = line if channel == "stable" else f"{line} ({channel})"

    return {
        "player_version": raw,
        "player_major": major,
        "player_minor": minor,
        "player_patch": patch,
        "player_line": line,
        "player_channel": channel,
        "player_group": group,
    }


def player_info_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    cached = str(profile.get("player_version") or "").strip() or None
    info = classify_player_version(cached)
    info["player_version_source"] = profile.get("player_version_source") or None
    info["player_version_checked_at"] = profile.get("player_version_checked_at") or None
    return info


def enrich_target_record(name: str, profile: dict[str, Any]) -> dict[str, Any]:
    device = device_type_info(profile)
    player = player_info_from_profile(profile)
    return {
        "name": name,
        "label": profile.get("label") or "",
        "base_url": profile.get("base_url") or "",
        **device,
        **player,
    }


def persist_player_version(name: str, check: dict[str, Any]) -> None:
    """Lưu kết quả audit phiên bản FPP vào profile target."""
    fields: dict[str, Any] = {
        "player_version_source": check.get("source") or "",
        "player_version_checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if check.get("version"):
        fields["player_version"] = check["version"]
    project.upsert_target(name, fields, make_default=False)


def group_by_device_type(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        device_id = rec.get("device_type") or "unknown"
        groups[device_id].append(rec["name"])
    summary = []
    for device_id in sorted(groups, key=lambda k: DEVICE_TYPES.get(k, {}).get("label", k)):
        meta = DEVICE_TYPES.get(device_id, {"label": device_id})
        summary.append(
            {
                "device_type": device_id,
                "device_label": meta.get("label", device_id),
                "count": len(groups[device_id]),
                "targets": groups[device_id],
            }
        )
    return {"groups": summary, "total": len(records)}


def group_by_player_version(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        group = rec.get("player_group") or "unknown"
        groups[group].append(rec["name"])
    summary = []
    for group_key in sorted(groups):
        versions = sorted(
            {
                rec.get("player_version")
                for rec in records
                if rec.get("name") in groups[group_key] and rec.get("player_version")
            }
        )
        summary.append(
            {
                "player_group": group_key,
                "count": len(groups[group_key]),
                "targets": groups[group_key],
                "versions": versions,
            }
        )
    return {"groups": summary, "total": len(records)}


def build_catalog(*, include_stale: bool = True) -> dict[str, Any]:
    """Phân loại toàn bộ target theo device + player version đã lưu."""
    listing = dev_target.list_targets(mask_secrets=True)
    records: list[dict[str, Any]] = []
    for item in listing["targets"]:
        profile = project.get_target_profile(item["name"])
        records.append(enrich_target_record(item["name"], profile))

    return {
        "target_count": listing["count"],
        "default_target": listing.get("default_target"),
        "active_target": listing.get("active_target"),
        "device_types_available": list_device_types(),
        "targets": records,
        "by_device_type": group_by_device_type(records),
        "by_player_version": group_by_player_version(records),
        "include_stale": include_stale,
    }


def apply_check_classifications(check: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Gắn device + player class vào một kết quả audit."""
    enriched = dict(check)
    enriched.update(device_type_info(profile))
    player = classify_player_version(check.get("version"))
    enriched.update(player)
    return enriched
