#!/usr/bin/env python3
"""Generate AUTO section in SKILL_EXPERIENCES.md from experiences_bundled.json."""

from __future__ import annotations

import json
from pathlib import Path

AUTO_BEGIN = "<!-- experiences:auto:begin -->"
AUTO_END = "<!-- experiences:auto:end -->"

SCOPE_ORDER = ("global", "device", "player")
SCOPE_TITLES = {
    "global": "Global (mọi target)",
    "device": "Device-specific",
    "player": "Player-specific (FPP version)",
}


def repo_paths() -> tuple[Path, Path]:
    here = Path(__file__).resolve()
    harness = here.parents[1]
    bundled = harness / "cli_fpp" / "skills" / "experiences_bundled.json"
    skill_md = harness / "cli_fpp" / "skills" / "SKILL_EXPERIENCES.md"
    return bundled, skill_md


def load_bundled(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def render_auto_section(entries: list[dict]) -> str:
    lines = [
        AUTO_BEGIN,
        "",
        "### Bundled experiences (auto từ JSON)",
        "",
        "> Chạy `python agent-harness/scripts/generate_experiences_skill.py` sau khi sửa `experiences_bundled.json`.",
        "",
    ]
    by_scope: dict[str, list[dict]] = {s: [] for s in SCOPE_ORDER}
    for entry in entries:
        scope = entry.get("scope", "global")
        by_scope.setdefault(scope, []).append(entry)

    for scope in SCOPE_ORDER:
        group = by_scope.get(scope) or []
        if not group:
            continue
        lines.append(f"#### {SCOPE_TITLES.get(scope, scope)}")
        lines.append("")
        for e in group:
            title = e.get("title", "")
            body = e.get("body", "")
            tags = ", ".join(e.get("tags") or [])
            extra = []
            if e.get("device_type"):
                extra.append(f"device={e['device_type']}")
            if e.get("player_line"):
                extra.append(f"player={e['player_line']}")
            if e.get("suggest_override"):
                so = e["suggest_override"]
                extra.append(f"override intent={so.get('when_intent')}")
            meta = f" ({', '.join(extra)})" if extra else ""
            tag_suffix = f" `[{tags}]`" if tags else ""
            lines.append(f"- **{title}**{tag_suffix}{meta}: {body}")
        lines.append("")

    lines.append(AUTO_END)
    return "\n".join(lines)


def merge_into_skill_md(skill_path: Path, auto_block: str) -> None:
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
    else:
        text = (
            "## Kinh nghiệm thực tế (so sánh UI ↔ API ↔ CLI)\n\n"
            "> Cập nhật bundled JSON + chạy generator.\n\n"
        )

    if AUTO_BEGIN in text and AUTO_END in text:
        before = text.split(AUTO_BEGIN)[0].rstrip()
        after = text.split(AUTO_END)[1].lstrip()
        merged = before + "\n\n" + auto_block + "\n\n" + after
    else:
        merged = text.rstrip() + "\n\n" + auto_block + "\n"

    skill_path.write_text(merged, encoding="utf-8")


def main() -> int:
    bundled_path, skill_path = repo_paths()
    entries = load_bundled(bundled_path)
    auto_block = render_auto_section(entries)
    merge_into_skill_md(skill_path, auto_block)
    print(f"Updated {skill_path} ({len(entries)} bundled entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
