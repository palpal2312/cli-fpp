"""Auto-capture usage insights and contribute back to the cli-fpp repo."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cli_fpp import __version__
from cli_fpp.core import experiences as exp_mod
from cli_fpp.core import project

CONTRIB_QUEUE_FILE = project.CONFIG_DIR / "contrib_queue.jsonl"
CONTRIB_STATE_FILE = project.CONFIG_DIR / "contrib_state.json"
SCHEMA_VERSION = "cli-fpp-contribution/v1"

# Relative to repo root (cli-anything-fpp)
INBOX_REL = Path("agent-harness/cli_fpp/skills/contributions/inbox")
DEFAULT_GITHUB_UPSTREAM = os.environ.get("CLI_FPP_GITHUB_REPO", "palpal2312/cli-anything-fpp")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"(-p|--password)\s+\S+", r"\1 ****", text, flags=re.I)
    text = re.sub(r"(-u|--user)\s+\S+", r"\1 ****", text, flags=re.I)
    text = re.sub(r"(password|passwd|secret)[\"']?\s*[:=]\s*[\"']?[^\s\"']+", r"\1=****", text, flags=re.I)
    text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "HOST", text)
    return text


def _fingerprint(title: str, body: str, scope: str) -> str:
    raw = f"{scope}|{title.strip().lower()}|{body.strip().lower()[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def contrib_enabled() -> bool:
    cfg = project.load_raw_config()
    if "contrib_enabled" in cfg:
        return bool(cfg.get("contrib_enabled"))
    return os.environ.get("CLI_FPP_CONTRIB", "1").strip().lower() not in ("0", "false", "no")


def _load_state() -> dict[str, Any]:
    if not CONTRIB_STATE_FILE.exists():
        return {"exported_fps": [], "submitted_ids": []}
    try:
        return json.loads(CONTRIB_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return {"exported_fps": [], "submitted_ids": []}


def _save_state(state: dict[str, Any]) -> None:
    project.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONTRIB_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_queue_lines() -> list[dict[str, Any]]:
    if not CONTRIB_QUEUE_FILE.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in CONTRIB_QUEUE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def queue_status() -> dict[str, Any]:
    items = _load_queue_lines()
    pending = [i for i in items if i.get("status", "pending") == "pending"]
    by_scope: dict[str, int] = {}
    for item in pending:
        scope = item.get("scope", "global")
        by_scope[scope] = by_scope.get(scope, 0) + 1
    gh_info: dict[str, Any] = {}
    try:
        from cli_fpp.core import github_auth

        gh_info = github_auth.diagnostic()
    except Exception as exc:
        gh_info = {"error": str(exc)}
    return {
        "enabled": contrib_enabled(),
        "queue_file": str(CONTRIB_QUEUE_FILE),
        "total": len(items),
        "pending": len(pending),
        "by_scope": by_scope,
        "inbox_path": str(INBOX_REL),
        "github": gh_info,
        "upstream": DEFAULT_GITHUB_UPSTREAM,
    }


def capture(
    *,
    title: str,
    body: str,
    kind: str = "insight",
    scope: str | None = None,
    device_type: str | None = None,
    player_line: str | None = None,
    player_version: str | None = None,
    source_command: str | None = None,
    exit_code: int | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append one contribution candidate to local queue (deduped)."""
    if not contrib_enabled():
        return None

    title = _redact(title.strip())
    body = _redact(body.strip())
    if not title or not body:
        return None

    resolved_scope = scope or exp_mod.SCOPE_GLOBAL
    fp = _fingerprint(title, body, resolved_scope)
    existing = _load_queue_lines()
    if any(e.get("fingerprint") == fp and e.get("status") == "pending" for e in existing):
        return None

    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "ts": _now_iso(),
        "kind": kind,
        "scope": resolved_scope,
        "device_type": device_type,
        "player_line": player_line,
        "player_version": player_version,
        "title": title,
        "body": body,
        "source_command": _redact(source_command or ""),
        "exit_code": exit_code,
        "context": {k: v for k, v in (context or {}).items() if k not in ("password", "ssh_password")},
        "fingerprint": fp,
        "status": "pending",
        "cli_version": __version__,
    }

    project.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONTRIB_QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def capture_from_insights(
    insights: list[str],
    *,
    command: str = "",
    output: str = "",
    exit_code: int | None = None,
) -> list[dict[str, Any]]:
    """Map pre-extracted shell insights to scoped queue entries."""
    ctx = exp_mod.get_context()
    captured: list[dict[str, Any]] = []
    for insight in insights:
        scope = exp_mod.SCOPE_GLOBAL
        device_type = None
        player_line = None
        lower = insight.lower()
        if any(k in lower for k in ("orangepi", "rk356x", "fb0", "rotate", "reboot", "ssh")):
            scope = exp_mod.SCOPE_DEVICE
            device_type = ctx.get("device_type")
        if any(k in lower for k in ("fpp", "fppd", "8.", "version", "limonade", "api/")):
            if ctx.get("player_line") and ctx["player_line"] != "unknown":
                scope = exp_mod.SCOPE_PLAYER
                player_line = ctx.get("player_line")
        item = capture(
            title=insight[:80],
            body=insight,
            kind="shell_insight" if exit_code == 0 else "shell_error",
            scope=scope,
            device_type=device_type,
            player_line=player_line,
            source_command=command,
            exit_code=exit_code,
            context=ctx,
        )
        if item:
            captured.append(item)
    return captured


def capture_from_shell(command: str, output: str, exit_code: int | None) -> list[dict[str, Any]]:
    """Extract insights (sync_skill_hooks rules) and enqueue scoped contributions."""
    insights = _shell_insights(command, output, exit_code)
    return capture_from_insights(
        insights,
        command=command,
        output=output,
        exit_code=exit_code,
    )


def _shell_insights(command: str, output: str, exit_code: int | None) -> list[str]:
    """Reuse sync_skill_hooks.extract_insights when repo script is on disk."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "sync_skill_hooks.py"
    if script.exists():
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("_sync_skill_hooks", script)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return list(mod.extract_insights(command, output, exit_code))
        except Exception:
            pass
    cmd_l = (command or "").lower()
    if "cli-fpp" not in cmd_l and "cli_fpp" not in cmd_l:
        return []
    out = output or ""
    insights: list[str] = []
    if "WRONG_VERSION_NUMBER" in out or ("SSLError" in out and "https://" in command):
        insights.append("HTTPS trên port 81 → SSLError; dùng http://HOST:81")
    if exit_code and exit_code != 0:
        if "401" in out or "Unauthorized" in out:
            insights.append("Thiếu auth → 401; cấu hình username/password trong target profile")
        if "base URL not configured" in out:
            insights.append("Chưa cấu hình URL — target add hoặc --url")
    if "limonade.php" in out:
        insights.append("Route lỗi limonade PHP → dùng player status thay system status")
    return insights


def capture_from_audit(audit: dict[str, Any]) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    for check in audit.get("checks") or []:
        if check.get("ok"):
            ver = check.get("player_version") or check.get("version")
            if ver:
                item = capture(
                    title=f"FPP {ver} reachable on {check.get('name')}",
                    body=f"Xác minh player version {ver} qua {check.get('source', 'audit')}.",
                    kind="audit_ok",
                    scope=exp_mod.SCOPE_PLAYER,
                    player_line=check.get("player_line"),
                    player_version=ver,
                    device_type=check.get("device_type"),
                    context={"target": check.get("name")},
                )
                if item:
                    captured.append(item)
        elif check.get("error"):
            item = capture(
                title=f"Audit failed: {check.get('name')}",
                body=str(check.get("error")),
                kind="audit_error",
                scope=exp_mod.SCOPE_DEVICE if check.get("device_type") else exp_mod.SCOPE_GLOBAL,
                device_type=check.get("device_type"),
                player_line=check.get("player_line"),
                context={"target": check.get("name")},
            )
            if item:
                captured.append(item)
    return captured


def capture_remembered(entry: dict[str, Any]) -> dict[str, Any] | None:
    return capture(
        title=entry.get("title", "User experience"),
        body=entry.get("body", ""),
        kind="remember",
        scope=entry.get("scope", exp_mod.SCOPE_GLOBAL),
        device_type=entry.get("device_type"),
        player_line=entry.get("player_line"),
        player_version=entry.get("player_version"),
        context={"applies_to": entry.get("applies_to")},
    )


def capture_cli_error(exc: Exception, *, command_hint: str = "") -> dict[str, Any] | None:
    ctx = exp_mod.get_context()
    return capture(
        title=type(exc).__name__,
        body=str(exc),
        kind="cli_error",
        scope=exp_mod.SCOPE_GLOBAL,
        source_command=command_hint,
        exit_code=1,
        context=ctx,
    )


def find_repo_root(start: Path | None = None) -> Path | None:
    env = os.environ.get("CLI_FPP_REPO", "").strip()
    if env:
        p = Path(env)
        if (p / "agent-harness" / "cli_fpp" / "skills" / "contributions").exists() or (
            p / "agent-harness" / "scripts" / "build_skill_md.py"
        ).exists():
            return p.resolve()
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "agent-harness" / "scripts" / "build_skill_md.py").exists():
            return candidate
        if (candidate / "cli-anything-fpp" / "agent-harness" / "scripts" / "build_skill_md.py").exists():
            return (candidate / "cli-anything-fpp").resolve()
    # Installed package skills path
    pkg_skills = Path(__file__).resolve().parent.parent / "skills" / "contributions"
    if pkg_skills.exists():
        return pkg_skills.parent.parent.parent.parent  # may not be git repo
    return None


def build_export_payload(*, pending_only: bool = True) -> dict[str, Any]:
    items = _load_queue_lines()
    if pending_only:
        items = [i for i in items if i.get("status") == "pending"]
    return {
        "schema": SCHEMA_VERSION,
        "exported_at": _now_iso(),
        "cli_version": __version__,
        "anonymous": True,
        "entry_count": len(items),
        "entries": items,
        "scope_legend": exp_mod.SCOPE_META,
        "priority_hint": exp_mod.PRIORITY_HINT,
    }


def export_pending(*, mark_exported: bool = True) -> dict[str, Any]:
    payload = build_export_payload(pending_only=True)
    if mark_exported and payload["entries"]:
        fps = {e["fingerprint"] for e in payload["entries"]}
        lines = _load_queue_lines()
        for item in lines:
            if item.get("fingerprint") in fps and item.get("status") == "pending":
                item["status"] = "exported"
        CONTRIB_QUEUE_FILE.write_text(
            "\n".join(json.dumps(i, ensure_ascii=False) for i in lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )
        state = _load_state()
        state["exported_fps"] = sorted(set(state.get("exported_fps", [])) | fps)
        _save_state(state)
    return payload


def submit_to_repo(
    repo_root: Path | str | None = None,
    *,
    pending_only: bool = True,
) -> dict[str, Any]:
    """Write pending contributions to repo contributions/inbox/ for PR."""
    root = Path(repo_root) if repo_root else find_repo_root()
    if not root:
        raise FileNotFoundError(
            "Không tìm thấy repo cli-anything-fpp. "
            "Set CLI_FPP_REPO hoặc chạy từ clone repo, hoặc dùng: experience contribute export"
        )
    inbox = root / INBOX_REL
    inbox.mkdir(parents=True, exist_ok=True)

    payload = export_pending(mark_exported=True)
    if not payload["entries"]:
        return {"submitted": False, "reason": "Không có entry pending", "inbox": str(inbox)}

    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}.json"
    out_path = inbox / fname
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    state = _load_state()
    state.setdefault("submitted_files", []).append(str(out_path))
    _save_state(state)

    return {
        "submitted": True,
        "file": str(out_path),
        "entry_count": payload["entry_count"],
        "next_steps": [
            f"Review file: {out_path}",
            "git add agent-harness/cli_fpp/skills/contributions/inbox/",
            "git commit -m \"contrib: add field experiences\"",
            "git push && open PR",
            "Maintainer: python agent-harness/scripts/merge_contributions.py --dry-run",
        ],
    }


def submit_via_github(upstream: str | None = None) -> dict[str, Any]:
    """Fork + branch + file + PR via gh API (không cần clone repo local)."""
    from cli_fpp.core import github_auth

    repo = (upstream or DEFAULT_GITHUB_UPSTREAM).strip()
    if "/" not in repo:
        raise ValueError("upstream phải dạng owner/repo hoặc set CLI_FPP_GITHUB_REPO")

    payload = export_pending(mark_exported=True)
    if not payload["entries"]:
        return {"submitted": False, "reason": "Không có entry pending", "upstream": repo}

    token = github_auth.get_token().token
    user = github_auth.get_github_username(token=token)
    if not user:
        raise github_auth.GitHubAuthError("Không lấy được GitHub username — chạy: cli-fpp experience contribute login")

    fork = github_auth.ensure_fork(repo, token=token)
    fork_owner = fork.split("/", 1)[0]

    repo_info = github_auth.run_gh_api("GET", f"repos/{fork}", token=token)
    base_branch = repo_info.get("default_branch") or "main"
    ref = github_auth.run_gh_api("GET", f"repos/{fork}/git/ref/heads/{base_branch}", token=token)
    base_sha = ref["object"]["sha"]

    branch = f"contrib/{user}-{uuid.uuid4().hex[:8]}"
    github_auth.run_gh_api(
        "POST",
        f"repos/{fork}/git/refs",
        token=token,
        input_json={"ref": f"refs/heads/{branch}", "sha": base_sha},
    )

    fname = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}.json"
    rel_path = str(INBOX_REL / fname).replace("\\", "/")
    body_bytes = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    github_auth.run_gh_api(
        "PUT",
        f"repos/{fork}/contents/{rel_path}",
        token=token,
        input_json={
            "message": f"contrib: {payload['entry_count']} field experience(s) from {user}",
            "content": base64.b64encode(body_bytes).decode("ascii"),
            "branch": branch,
        },
    )

    pr = github_auth.run_gh_api(
        "POST",
        f"repos/{repo}/pulls",
        token=token,
        input_json={
            "title": f"contrib: field experiences from @{user}",
            "head": f"{fork_owner}:{branch}",
            "base": base_branch,
            "body": (
                "Auto-submitted via `cli-fpp experience contribute submit --github`.\n\n"
                f"Entries: {payload['entry_count']}\n"
                f"Schema: {SCHEMA_VERSION}"
            ),
        },
    )

    state = _load_state()
    state.setdefault("submitted_prs", []).append(pr.get("html_url"))
    _save_state(state)

    return {
        "submitted": True,
        "method": "github",
        "upstream": repo,
        "fork": fork,
        "branch": branch,
        "file": rel_path,
        "entry_count": payload["entry_count"],
        "pr_url": pr.get("html_url"),
        "pr_number": pr.get("number"),
    }


def promote_to_local_experiences(*, limit: int = 10) -> dict[str, Any]:
    """Copy pending queue entries into ~/.cli-fpp/experiences.json (user library)."""
    items = [i for i in _load_queue_lines() if i.get("status") == "pending"][:limit]
    promoted: list[str] = []
    for item in items:
        result = exp_mod.add_experience(
            title=item["title"],
            body=item["body"],
            scope=item.get("scope", exp_mod.SCOPE_GLOBAL),
            device_type=item.get("device_type"),
            player_line=item.get("player_line"),
            player_version=item.get("player_version"),
            source="contrib_queue",
        )
        promoted.append(result["entry"]["id"])
    return {"promoted": promoted, "count": len(promoted)}
