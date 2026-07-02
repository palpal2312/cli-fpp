#!/usr/bin/env python3
"""Merge user contribution inbox files into experiences_bundled.json (maintainer)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def repo_paths() -> tuple[Path, Path, Path]:
    here = Path(__file__).resolve()
    root = here.parents[1]
    bundled = root / "cli_fpp" / "skills" / "experiences_bundled.json"
    inbox = root / "cli_fpp" / "skills" / "contributions" / "inbox"
    return root, bundled, inbox


def _slug_id(title: str, scope: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    return f"{scope}.{slug or 'entry'}"


def _fingerprint(title: str, body: str, scope: str) -> str:
    raw = f"{scope}|{title.strip().lower()}|{body.strip().lower()[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_bundled(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def bundled_fps(entries: list[dict]) -> set[str]:
    fps: set[str] = set()
    for e in entries:
        fps.add(_fingerprint(e.get("title", ""), e.get("body", ""), e.get("scope", "global")))
    return fps


def collect_inbox(inbox: Path) -> list[dict]:
    candidates: list[dict] = []
    if not inbox.exists():
        return candidates
    for path in sorted(inbox.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for entry in payload.get("entries") or []:
            entry["_source_file"] = path.name
            candidates.append(entry)
    return candidates


def to_bundled_entry(entry: dict) -> dict:
    scope = entry.get("scope", "global")
    title = str(entry.get("title", "")).strip()
    body = str(entry.get("body", "")).strip()
    out: dict = {
        "id": _slug_id(title, scope),
        "scope": scope,
        "title": title,
        "body": body,
        "tags": entry.get("tags") or ["contrib"],
        "source": "contrib",
    }
    if entry.get("device_type"):
        out["device_type"] = entry["device_type"]
    if entry.get("player_line"):
        out["player_line"] = entry["player_line"]
    if entry.get("player_version"):
        out["player_version"] = entry["player_version"]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge contrib inbox → experiences_bundled.json")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in báo cáo, không ghi file")
    parser.add_argument("--report", action="store_true", help="In metrics (mặc định nếu không --apply)")
    parser.add_argument("--apply", action="store_true", help="Ghi entry mới vào bundled")
    args = parser.parse_args()
    if not args.dry_run and not args.apply and not args.report:
        args.dry_run = True
    if args.report and not args.apply:
        args.dry_run = True

    _root, bundled_path, inbox = repo_paths()
    bundled = load_bundled(bundled_path)
    existing_ids = {e.get("id") for e in bundled}
    existing_fps = bundled_fps(bundled)

    inbox_entries = collect_inbox(inbox)
    new_entries: list[dict] = []
    skipped = 0
    for raw in inbox_entries:
        fp = raw.get("fingerprint") or _fingerprint(
            raw.get("title", ""), raw.get("body", ""), raw.get("scope", "global")
        )
        if fp in existing_fps:
            skipped += 1
            continue
        candidate = to_bundled_entry(raw)
        if candidate["id"] in existing_ids:
            candidate["id"] = f"{candidate['id']}-{fp[:6]}"
        new_entries.append(candidate)
        existing_fps.add(fp)
        existing_ids.add(candidate["id"])

    report = {
        "inbox_files": len(list(inbox.glob("*.json"))) if inbox.exists() else 0,
        "inbox_entries": len(inbox_entries),
        "bundled_count": len(bundled),
        "skipped_duplicate": skipped,
        "new_entries": len(new_entries),
        "preview": new_entries[:5],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.apply and new_entries:
        merged = bundled + new_entries
        bundled_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {len(new_entries)} entries to {bundled_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
