"""Kinh nghiệm theo Target (device) và Player (FPP version) — lưu trên controller."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli_fpp.core import project
from cli_fpp.core import target_catalog

CONFIG_DIR = project.CONFIG_DIR
EXPERIENCES_FILE = CONFIG_DIR / "experiences.json"
BUNDLED_FILE = Path(__file__).resolve().parent.parent / "skills" / "experiences_bundled.json"

SCOPE_GLOBAL = "global"
SCOPE_DEVICE = "device"
SCOPE_PLAYER = "player"
SCOPES = (SCOPE_GLOBAL, SCOPE_DEVICE, SCOPE_PLAYER)

SCOPE_META: dict[str, dict[str, str]] = {
    SCOPE_GLOBAL: {
        "scope_label": "Kinh nghiệm chung",
        "scope_hint": "Áp dụng mọi target — không phụ thuộc loại thiết bị hay phiên bản FPP.",
        "applies_when": "Luôn luôn (controller → bất kỳ target nào).",
    },
    SCOPE_DEVICE: {
        "scope_label": "Kinh nghiệm riêng Target (thiết bị)",
        "scope_hint": "Chỉ áp dụng khi target có cùng device_type (Orange Pi, RPi, …).",
        "applies_when": "Khi device_type của target khớp với entry.",
    },
    SCOPE_PLAYER: {
        "scope_label": "Kinh nghiệm riêng Player (FPP version)",
        "scope_hint": "Chỉ áp dụng khi player_line hoặc player_version khớp.",
        "applies_when": "Sau target audit hoặc khi đã biết FPP version trên target.",
    },
}

PRIORITY_HINT = (
    "Ưu tiên khi xử lý: player-specific > device-specific > global. "
    "Kinh nghiệm riêng ghi đè/giới hạn cách hiểu kinh nghiệm chung."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_bundled() -> list[dict[str, Any]]:
    if not BUNDLED_FILE.exists():
        return []
    try:
        data = json.loads(BUNDLED_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError, ValueError):
        pass
    return []


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    out.setdefault("id", str(uuid.uuid4())[:12])
    out.setdefault("scope", SCOPE_GLOBAL)
    out.setdefault("tags", [])
    out.setdefault("source", "user")
    out.setdefault("created_at", _now_iso())
    out.setdefault("updated_at", out["created_at"])
    if out.get("device_type"):
        out["device_type"] = target_catalog.normalize_device_type(str(out["device_type"]))
    if out.get("player_line") and out["player_line"] != "unknown":
        out["player_line"] = str(out["player_line"]).strip()
    return out


def load_store(*, merge_bundled: bool = True) -> dict[str, Any]:
    store: dict[str, Any] = {"version": 1, "entries": []}
    if EXPERIENCES_FILE.exists():
        try:
            loaded = json.loads(EXPERIENCES_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("entries"), list):
                store = loaded
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    if merge_bundled:
        by_id = {e.get("id"): e for e in store["entries"] if e.get("id")}
        for bundled in _load_bundled():
            bid = bundled.get("id")
            if not bid or bid in by_id:
                continue
            entry = _normalize_entry({**bundled, "source": "bundled"})
            store["entries"].append(entry)
            by_id[bid] = entry
    return store


def save_store(store: dict[str, Any]) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXPERIENCES_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
    return EXPERIENCES_FILE


def get_context(*, target_name: str | None = None) -> dict[str, Any]:
    """Device + player context từ target profile."""
    raw = project.load_raw_config()
    name = target_name or project.get_active_target_name(raw=raw) or raw.get("default_target")
    ctx: dict[str, Any] = {
        "target_name": name,
        "device_type": None,
        "device_label": None,
        "player_version": None,
        "player_line": None,
        "player_group": None,
    }
    if not name:
        return ctx
    try:
        profile = project.get_target_profile(str(name), raw=raw)
    except KeyError:
        return ctx
    device = target_catalog.device_type_info(profile)
    player = target_catalog.player_info_from_profile(profile)
    ctx.update(device)
    ctx.update(player)
    return ctx


def _device_label(device_type: str | None) -> str:
    if not device_type:
        return "?"
    return target_catalog.DEVICE_TYPES.get(device_type, {}).get("label", device_type)


def _applies_to_text(entry: dict[str, Any]) -> str:
    scope = entry.get("scope", SCOPE_GLOBAL)
    if scope == SCOPE_GLOBAL:
        return "Mọi target"
    if scope == SCOPE_DEVICE:
        dt = entry.get("device_type")
        return f"Target device_type={dt} ({_device_label(dt)})"
    if scope == SCOPE_PLAYER:
        parts: list[str] = []
        if entry.get("player_version"):
            parts.append(f"FPP {entry['player_version']}")
        elif entry.get("player_line"):
            parts.append(f"FPP line {entry['player_line']}")
        if entry.get("device_type"):
            parts.append(f"trên {_device_label(entry['device_type'])}")
        return " + ".join(parts) if parts else "Player (chưa rõ version)"
    return "?"


def _match_reason(entry: dict[str, Any], ctx: dict[str, Any], score: int) -> str:
    scope = entry.get("scope", SCOPE_GLOBAL)
    if score <= 0:
        return "Không khớp context hiện tại"
    if scope == SCOPE_GLOBAL:
        return "Kinh nghiệm chung — luôn áp dụng"
    if scope == SCOPE_DEVICE:
        return (
            f"Target hiện tại là {_device_label(ctx.get('device_type'))} "
            f"(device_type={ctx.get('device_type')})"
        )
    if scope == SCOPE_PLAYER:
        if entry.get("player_version") and ctx.get("player_version") == entry.get("player_version"):
            return f"Khớp player_version={ctx.get('player_version')}"
        if entry.get("player_line") and ctx.get("player_line") == entry.get("player_line"):
            return f"Khớp player_line={ctx.get('player_line')}"
        return f"Khớp nhóm Player {ctx.get('player_group') or ctx.get('player_line')}"
    return "Khớp context"


def _match_score(entry: dict[str, Any], ctx: dict[str, Any]) -> int:
    scope = entry.get("scope", SCOPE_GLOBAL)
    if scope == SCOPE_GLOBAL:
        return 10
    score = 0
    if scope == SCOPE_DEVICE:
        want = entry.get("device_type")
        if not want:
            return 0
        if ctx.get("device_type") == want:
            score = 80
        else:
            return 0
    elif scope == SCOPE_PLAYER:
        want_line = entry.get("player_line")
        want_ver = entry.get("player_version")
        if want_ver and ctx.get("player_version") == want_ver:
            score = 100
        elif want_line and ctx.get("player_line") == want_line:
            score = 70
        elif want_line and ctx.get("player_group") and want_line in str(ctx.get("player_group")):
            score = 60
        else:
            return 0
    if entry.get("target_name") and ctx.get("target_name") == entry.get("target_name"):
        score += 20
    return score


def enrich_entry(entry: dict[str, Any], ctx: dict[str, Any], *, score: int | None = None) -> dict[str, Any]:
    """Gắn metadata để CLI/agent hiểu tầng kinh nghiệm."""
    scope = entry.get("scope", SCOPE_GLOBAL)
    resolved_score = score if score is not None else _match_score(entry, ctx)
    meta = SCOPE_META.get(scope, SCOPE_META[SCOPE_GLOBAL])
    item = dict(entry)
    item.update(
        {
            "scope": scope,
            "scope_label": meta["scope_label"],
            "scope_hint": meta["scope_hint"],
            "applies_to": _applies_to_text(entry),
            "match_score": resolved_score,
            "matches_context": resolved_score > 0,
            "match_reason": _match_reason(entry, ctx, resolved_score),
            "specificity": {"global": 0, "device": 1, "player": 2}.get(scope, 0),
        }
    )
    return item


def partition_layers(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    layers: dict[str, list[dict[str, Any]]] = {
        SCOPE_GLOBAL: [],
        SCOPE_DEVICE: [],
        SCOPE_PLAYER: [],
    }
    for entry in entries:
        scope = entry.get("scope", SCOPE_GLOBAL)
        if scope in layers:
            layers[scope].append(entry)
        else:
            layers[SCOPE_GLOBAL].append(entry)
    return layers


def list_experiences(
    *,
    target_name: str | None = None,
    device_type: str | None = None,
    player_line: str | None = None,
    tag: str | None = None,
    include_global: bool = True,
    min_score: int = 1,
    include_non_matching: bool = False,
) -> dict[str, Any]:
    ctx = get_context(target_name=target_name)
    if device_type:
        ctx["device_type"] = target_catalog.normalize_device_type(device_type)
        ctx["device_label"] = _device_label(ctx["device_type"])
    if player_line:
        ctx["player_line"] = player_line

    store = load_store()
    matched: list[dict[str, Any]] = []
    non_matching: list[dict[str, Any]] = []
    for entry in store["entries"]:
        if not include_global and entry.get("scope") == SCOPE_GLOBAL:
            continue
        if tag and tag not in (entry.get("tags") or []):
            continue
        score = _match_score(entry, ctx)
        enriched = enrich_entry(entry, ctx, score=score)
        if score >= min_score:
            matched.append(enriched)
        elif include_non_matching and entry.get("scope") != SCOPE_GLOBAL:
            enriched["match_reason"] = _match_reason(entry, ctx, 0)
            non_matching.append(enriched)

    matched.sort(key=lambda e: (-e["specificity"], -e["match_score"], e.get("title", "")))
    layers = partition_layers(matched)

    return {
        "context": ctx,
        "priority_hint": PRIORITY_HINT,
        "scope_legend": SCOPE_META,
        "count": len(matched),
        "layers": {
            SCOPE_GLOBAL: {
                **SCOPE_META[SCOPE_GLOBAL],
                "count": len(layers[SCOPE_GLOBAL]),
                "entries": layers[SCOPE_GLOBAL],
            },
            SCOPE_DEVICE: {
                **SCOPE_META[SCOPE_DEVICE],
                "count": len(layers[SCOPE_DEVICE]),
                "entries": layers[SCOPE_DEVICE],
            },
            SCOPE_PLAYER: {
                **SCOPE_META[SCOPE_PLAYER],
                "count": len(layers[SCOPE_PLAYER]),
                "entries": layers[SCOPE_PLAYER],
            },
        },
        "entries": matched,
        "non_matching_device_or_player": non_matching,
        "by_scope": {k: len(v) for k, v in layers.items()},
    }


def get_experience(entry_id: str, *, target_name: str | None = None) -> dict[str, Any]:
    store = load_store()
    ctx = get_context(target_name=target_name)
    for entry in store["entries"]:
        if entry.get("id") == entry_id:
            return enrich_entry(entry, ctx)
    raise KeyError(f"Experience not found: {entry_id}")


def add_experience(
    *,
    title: str,
    body: str,
    scope: str = SCOPE_GLOBAL,
    device_type: str | None = None,
    player_line: str | None = None,
    player_version: str | None = None,
    target_name: str | None = None,
    tags: list[str] | None = None,
    entry_id: str | None = None,
    source: str = "user",
) -> dict[str, Any]:
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of: {', '.join(SCOPES)}")
    if scope == SCOPE_DEVICE and not device_type:
        raise ValueError("scope=device cần --device-type")
    if scope == SCOPE_PLAYER and not (player_line or player_version):
        raise ValueError("scope=player cần --player-line hoặc --player-version")
    if not title.strip() or not body.strip():
        raise ValueError("title và body không được rỗng")

    entry = _normalize_entry(
        {
            "id": entry_id or _slug_id(title, scope),
            "scope": scope,
            "title": title.strip(),
            "body": body.strip(),
            "device_type": device_type,
            "player_line": player_line,
            "player_version": player_version,
            "target_name": target_name,
            "tags": tags or [],
            "source": source,
            "updated_at": _now_iso(),
        }
    )
    if entry.get("device_type"):
        entry["device_type"] = target_catalog.normalize_device_type(str(entry["device_type"]))

    store = load_store(merge_bundled=False)
    replaced = False
    for i, existing in enumerate(store["entries"]):
        if existing.get("id") == entry["id"]:
            if existing.get("source") == "bundled":
                raise ValueError(f"Không ghi đè bundled experience: {entry['id']}")
            entry["created_at"] = existing.get("created_at", entry["created_at"])
            store["entries"][i] = entry
            replaced = True
            break
    if not replaced:
        store["entries"].append(entry)

    path = save_store(store)
    enriched = enrich_entry(entry, get_context(target_name=target_name))
    result = {"saved": str(path), "entry": enriched, "replaced": replaced}
    if source in ("user",):
        try:
            from cli_fpp.core import experience_contrib as contrib_mod

            queued = contrib_mod.capture_remembered(enriched)
            if queued:
                result["contrib_queued"] = queued["id"]
        except Exception:
            pass
    return result


def remember_experience(
    text: str,
    *,
    target_name: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    """Ghi kinh nghiệm — tự chọn tầng device/player nếu không chỉ định scope."""
    ctx = get_context(target_name=target_name)
    body = text.strip()
    if not body:
        raise ValueError("Nội dung kinh nghiệm không được rỗng")

    auto_title = title or (body[:72] + "…" if len(body) > 72 else body)
    resolved_scope = scope
    device_type = None
    player_line = None
    player_version = None

    if resolved_scope is None:
        if ctx.get("player_line") and ctx["player_line"] != "unknown":
            resolved_scope = SCOPE_PLAYER
            player_line = ctx["player_line"]
            player_version = ctx.get("player_version")
            device_type = ctx.get("device_type")
        elif ctx.get("device_type"):
            resolved_scope = SCOPE_DEVICE
            device_type = ctx["device_type"]
        else:
            resolved_scope = SCOPE_GLOBAL
    elif resolved_scope == SCOPE_DEVICE:
        device_type = ctx.get("device_type")
        if not device_type:
            raise ValueError("scope=device nhưng target chưa có device_type — dùng target add --device-type")
    elif resolved_scope == SCOPE_PLAYER:
        player_line = ctx.get("player_line")
        player_version = ctx.get("player_version")
        device_type = ctx.get("device_type")
        if not player_line and not player_version:
            raise ValueError("scope=player nhưng chưa có player version — chạy target audit trước")

    return add_experience(
        title=auto_title,
        body=body,
        scope=resolved_scope,
        device_type=device_type,
        player_line=player_line if player_line and player_line != "unknown" else None,
        player_version=player_version,
        target_name=ctx.get("target_name"),
        tags=tags or [],
        source="user",
    )


def remove_experience(entry_id: str) -> dict[str, Any]:
    bundled_ids = {e.get("id") for e in _load_bundled()}
    if entry_id in bundled_ids:
        raise ValueError("Không xóa bundled experience — chỉ user entries")
    store = load_store(merge_bundled=False)
    before = len(store["entries"])
    kept = [e for e in store["entries"] if e.get("id") != entry_id]
    if len(kept) == before:
        raise KeyError(f"Experience not found: {entry_id}")
    removed = next(e for e in store["entries"] if e.get("id") == entry_id)
    if removed.get("source") == "bundled":
        raise ValueError("Không xóa bundled experience — chỉ user entries")
    store["entries"] = kept
    path = save_store(store)
    return {"removed": entry_id, "saved": str(path)}


def _compact(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "id": entry.get("id", ""),
        "scope": entry.get("scope", ""),
        "scope_label": entry.get("scope_label", ""),
        "applies_to": entry.get("applies_to", ""),
        "match_reason": entry.get("match_reason", ""),
        "title": entry.get("title", ""),
        "body": entry.get("body", ""),
    }


_SCOPE_PRIORITY = {SCOPE_GLOBAL: 0, SCOPE_DEVICE: 1, SCOPE_PLAYER: 2}


def suggest_override_for_intent(*, intent: str, target_name: str | None = None) -> dict[str, Any] | None:
    """Experience suggest_override cho intent (player > device > global)."""
    store = load_store()
    ctx = get_context(target_name=target_name)
    best: dict[str, Any] | None = None
    best_pri = -1
    for entry in store["entries"]:
        override = entry.get("suggest_override")
        if not isinstance(override, dict) or override.get("when_intent") != intent:
            continue
        scope = entry.get("scope", SCOPE_GLOBAL)
        score = _match_score(entry, ctx)
        if scope != SCOPE_GLOBAL and score <= 0:
            continue
        pri = _SCOPE_PRIORITY.get(scope, 0)
        if pri < best_pri:
            continue
        best_pri = pri
        best = dict(override)
        best["experience_id"] = entry.get("id")
    return best


def experiences_for_suggest(*, target_name: str | None = None, limit_per_layer: int = 3) -> dict[str, Any]:
    """Kinh nghiệm phân tầng cho suggest / agent — tách rõ chung vs riêng."""
    result = list_experiences(target_name=target_name, include_global=True)
    layers = result["layers"]

    def take(scope: str) -> list[dict[str, str]]:
        return [_compact(e) for e in layers[scope]["entries"][:limit_per_layer]]

    return {
        "priority_hint": result["priority_hint"],
        "scope_legend": {
            k: {"scope_label": v["scope_label"], "scope_hint": v["scope_hint"]}
            for k, v in SCOPE_META.items()
        },
        "context": result["context"],
        "global": take(SCOPE_GLOBAL),
        "device_specific": take(SCOPE_DEVICE),
        "player_specific": take(SCOPE_PLAYER),
    }


def catalog_summary(*, target_name: str | None = None) -> dict[str, Any]:
    """Toàn bộ kho kinh nghiệm — phân loại theo tầng, không chỉ entry khớp."""
    store = load_store()
    ctx = get_context(target_name=target_name)
    all_enriched = [enrich_entry(e, ctx, score=_match_score(e, ctx)) for e in store["entries"]]
    inventory = partition_layers(all_enriched)

    by_device: dict[str, list[dict[str, str]]] = {}
    for entry in inventory[SCOPE_DEVICE]:
        dt = entry.get("device_type") or "unknown"
        by_device.setdefault(dt, []).append(_compact(entry))

    by_player: dict[str, list[dict[str, str]]] = {}
    for entry in inventory[SCOPE_PLAYER]:
        key = entry.get("player_line") or entry.get("player_version") or "unknown"
        by_player.setdefault(str(key), []).append(_compact(entry))

    relevant = list_experiences(target_name=target_name, include_global=True)
    return {
        "context": ctx,
        "priority_hint": PRIORITY_HINT,
        "scope_legend": SCOPE_META,
        "inventory": {
            "global": {
                **SCOPE_META[SCOPE_GLOBAL],
                "count": len(inventory[SCOPE_GLOBAL]),
                "entries": [_compact(e) for e in inventory[SCOPE_GLOBAL]],
            },
            "device": {
                **SCOPE_META[SCOPE_DEVICE],
                "count": len(inventory[SCOPE_DEVICE]),
                "by_device_type": {
                    dt: {"device_label": _device_label(dt), "count": len(items), "entries": items}
                    for dt, items in sorted(by_device.items())
                },
            },
            "player": {
                **SCOPE_META[SCOPE_PLAYER],
                "count": len(inventory[SCOPE_PLAYER]),
                "by_player_line": {
                    line: {"count": len(items), "entries": items}
                    for line, items in sorted(by_player.items())
                },
            },
        },
        "relevant_for_active_target": relevant["layers"],
    }


def _slug_id(title: str, scope: str = SCOPE_GLOBAL) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:36]
    prefix = {"global": "user.global", "device": "user.device", "player": "user.player"}.get(scope, "user")
    return f"{prefix}.{slug or uuid.uuid4().hex[:8]}"
