#!/usr/bin/env python3
"""Sync SKILL_EXPERIENCES + SKILL.md after cli-fpp runs or agent sessions.

Used by Cursor hooks (.cursor/hooks/*) and can be run manually:
  python agent-harness/scripts/sync_skill_hooks.py --from-shell '<cmd>' --output '...' --exit 0
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    """cli-anything-fpp repo root."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1],
        Path.cwd(),
        Path.cwd() / "cli-anything-fpp",
        here.parents[2] / "cli-anything-fpp",
    ]
    for p in candidates:
        if (p / "agent-harness" / "scripts" / "build_skill_md.py").exists():
            return p
    return here.parents[1]


def paths() -> dict[str, Path]:
    root = repo_root()
    harness = root / "agent-harness"
    skills = harness / "cli_fpp" / "skills"
    return {
        "root": root,
        "harness": harness,
        "experiences": skills / "SKILL_EXPERIENCES.md",
        "run_log": skills / "SKILL_RUN_LOG.jsonl",
        "build_skill": harness / "scripts" / "build_skill_md.py",
    }


AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"


def extract_insights(command: str, output: str, exit_code: int | None) -> list[str]:
    """Derive comparable UI/API/CLI lessons from a shell run."""
    insights: list[str] = []
    cmd_l = command.lower()
    out = output or ""
    is_cli_fpp = "cli-fpp" in cmd_l or "cli_fpp" in cmd_l or "python -m cli_fpp" in cmd_l

    if not is_cli_fpp:
        return insights

    if "WRONG_VERSION_NUMBER" in out or ("SSLError" in out and "https://" in command):
        insights.append(
            "HTTPS trên port 81 → `SSLError: WRONG_VERSION_NUMBER`; dùng `http://IP:81`"
        )

    if exit_code and exit_code != 0:
        if "401" in out or "Unauthorized" in out:
            insights.append("Thiếu auth → 401; dùng `-u`/`-p` hoặc `config set username/password`")
        if "base URL not configured" in out:
            insights.append("Chưa cấu hình URL → `config set base_url` hoặc `--url` / `FPP_BASE_URL`")

    if "limonade.php" in out:
        insights.append(
            "Route lỗi limonade PHP → thay bằng `player status` / `player current` (không dùng `system status`)"
        )

    if exit_code == 0:
        if "player status" in cmd_l or "player status" in out[:200]:
            m = re.search(r'"globalPauseBetweenSequencesMS"\s*:\s*(\d+)', out)
            if m:
                ms = int(m.group(1))
                insights.append(
                    f"`player status` → Global Pause = {ms} ms ({ms / 1000:g}s) — trường `globalPauseBetweenSequencesMS`"
                )
            m = re.search(r'"name"\s*:\s*"([^"]+)"', out)
            if m and "Haruhi" not in m.group(1):
                insights.append(f"`player status` OK — playlist đang chạy: `{m.group(1)}`")
            elif m:
                insights.append(f"`player status` OK — playlist: `{m.group(1)}`")
            if '"type": "image"' in out:
                insights.append("Đang chiếu `type: image` — xem `currentEntry.imagePath`, `modelName`")
        if "player current" in cmd_l and exit_code == 0:
            insights.append("`player current` OK — dùng cho tóm tắt màn hình đang phát")

    # Dedupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in insights:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _redact_secrets(text: str) -> str:
    text = re.sub(r"(-p|--password)\s+\S+", r"\1 ****", text, flags=re.I)
    text = re.sub(r"(-u|--user)\s+\S+", r"\1 ****", text, flags=re.I)
    return text


def append_run_log(command: str, output: str, exit_code: int | None, insights: list[str]) -> None:
    p = paths()
    p["run_log"].parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "command": _redact_secrets(command[:500]),
        "exit_code": exit_code,
        "insights": insights,
        "output_preview": _redact_secrets((output or "")[:800]),
    }
    with p["run_log"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def merge_auto_journal(insights: list[str]) -> bool:
    """Append new insight bullets into SKILL_EXPERIENCES.md AUTO section."""
    if not insights:
        return False
    p = paths()
    exp = p["experiences"]
    if not exp.exists():
        return False

    text = exp.read_text(encoding="utf-8")
    if AUTO_START not in text:
        block = (
            "\n### Nhật ký tự động (hook)\n\n"
            f"{AUTO_START}\n"
            f"{AUTO_END}\n"
        )
        text = text.rstrip() + block

    start = text.index(AUTO_START) + len(AUTO_START)
    end = text.index(AUTO_END)
    existing = text[start:end]
    existing_lines = {ln.strip() for ln in existing.splitlines() if ln.strip().startswith("-")}

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_lines: list[str] = []
    for insight in insights:
        line = f"- {ts}: {insight}"
        if line not in existing_lines:
            new_lines.append(line)

    if not new_lines:
        return False

    updated = text[:end].rstrip() + "\n" + "\n".join(new_lines) + "\n" + text[end:]
    exp.write_text(updated, encoding="utf-8")
    return True


def rebuild_skill_md() -> int:
    p = paths()
    script = p["build_skill"]
    if not script.exists():
        return 1
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(p["root"]),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or "build_skill_md failed\n")
    return proc.returncode


def sync_from_shell(command: str, output: str = "", exit_code: int | None = None) -> dict:
    insights = extract_insights(command, output, exit_code)
    append_run_log(command, output, exit_code, insights)
    journal_updated = merge_auto_journal(insights)
    build_rc = rebuild_skill_md()
    contrib_captured: list[dict] = []
    try:
        from cli_fpp.core import experience_contrib as contrib

        contrib_captured = contrib.capture_from_insights(
            insights,
            command=command,
            output=output,
            exit_code=exit_code,
        )
    except Exception:
        pass
    return {
        "insights": insights,
        "journal_updated": journal_updated,
        "build_skill_md_rc": build_rc,
        "contrib_captured": len(contrib_captured),
    }


def sync_session_end() -> dict:
    """End of agent session: always rebuild SKILL.md from current experiences."""
    build_rc = rebuild_skill_md()
    return {"build_skill_md_rc": build_rc, "event": "sessionEnd"}


def read_hook_stdin() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync cli-fpp skill docs after runs")
    parser.add_argument("--event", choices=["shell", "session"], default="shell")
    parser.add_argument("--from-shell", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--exit", dest="exit_code", type=int, default=None)
    args = parser.parse_args()

    if args.event == "session":
        result = sync_session_end()
    else:
        cmd = args.from_shell
        out = args.output
        code = args.exit_code
        if not cmd:
            data = read_hook_stdin()
            cmd = data.get("command") or data.get("full_command") or data.get("cmd") or ""
            out = data.get("output") or data.get("stdout") or data.get("stderr") or ""
            code = data.get("exit_code", data.get("exitCode", code))
        result = sync_from_shell(cmd, out, code)

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("build_skill_md_rc", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
