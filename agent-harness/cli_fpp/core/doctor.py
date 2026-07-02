"""Controller health checks — system, auth, config, contribute (ClaudeKit doctor-style)."""

from __future__ import annotations

import platform
import shutil
import sys
from typing import Any

from cli_fpp import __version__
from cli_fpp.core import dev_target
from cli_fpp.core import experience_contrib as contrib_mod
from cli_fpp.core import github_auth
from cli_fpp.core import project


def _check_python() -> dict[str, Any]:
    ver = sys.version_info
    ok = ver >= (3, 10)
    return {
        "ok": ok,
        "version": platform.python_version(),
        "required": ">=3.10",
    }


def _check_cli_fpp() -> dict[str, Any]:
    return {"ok": True, "version": __version__}


def _check_config() -> dict[str, Any]:
    raw = project.load_raw_config()
    targets = project.list_target_names(raw=raw)
    return {
        "ok": True,
        "config_dir": str(project.CONFIG_DIR),
        "config_file": str(project.CONFIG_FILE),
        "target_count": len(targets),
        "default_target": raw.get("default_target") or None,
        "contrib_enabled": contrib_mod.contrib_enabled(),
    }


def _check_git() -> dict[str, Any]:
    installed = shutil.which("git") is not None
    version = None
    if installed:
        import subprocess

        try:
            proc = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = (proc.stdout or "").strip() if proc.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {"ok": installed, "version": version}


def _check_github() -> dict[str, Any]:
    status = github_auth.auth_status()
    token_ok = False
    token_method = None
    err = None
    try:
        tr = github_auth.get_token(use_cache=False)
        token_ok = True
        token_method = tr.method
    except github_auth.GitHubAuthError as exc:
        err = str(exc)

    ok = status.installed and status.version_ok and status.authenticated and token_ok
    fix_hint = None
    if not status.installed:
        fix_hint = "winget install GitHub.cli  # hoặc brew/apt install gh"
    elif not status.version_ok:
        fix_hint = github_auth.gh_upgrade_hint()
    elif not status.authenticated:
        fix_hint = "cli-fpp experience contribute login  # hoặc gh auth login -h github.com -w"

    return {
        "ok": ok,
        "installed": status.installed,
        "version": status.version,
        "version_ok": status.version_ok,
        "authenticated": status.authenticated,
        "username": status.username,
        "token_ok": token_ok,
        "token_method": token_method,
        "scopes": status.scopes,
        "error": err,
        "fix_hint": fix_hint,
    }


def _check_contrib() -> dict[str, Any]:
    st = contrib_mod.queue_status()
    hint = None
    if st.get("pending", 0) > 0:
        hint = "cli-fpp experience contribute submit --github"
    return {
        "ok": True,
        "enabled": st["enabled"],
        "pending": st["pending"],
        "queue_file": st["queue_file"],
        "submit_hint": hint,
    }


def run_doctor(
    *,
    include_target: bool = False,
    compose_dir: str | None = None,
    fix: bool = False,
    check_only: bool = False,
) -> dict[str, Any]:
    """Full controller diagnostic; optionally include dev target doctor."""
    checks: dict[str, Any] = {
        "python": _check_python(),
        "cli_fpp": _check_cli_fpp(),
        "config": _check_config(),
        "git": _check_git(),
        "github": _check_github(),
        "contrib": _check_contrib(),
    }

    fixes_applied: list[str] = []
    if fix and not checks["github"]["ok"]:
        gh = checks["github"]
        if gh.get("installed") and not gh.get("authenticated"):
            try:
                github_auth.login()
                checks["github"] = _check_github()
                fixes_applied.append("gh auth login")
            except github_auth.GitHubAuthError as exc:
                checks["github"]["fix_error"] = str(exc)

    if include_target:
        checks["target"] = dev_target.dev_doctor(compose_dir=compose_dir)

    failed = [name for name, c in checks.items() if isinstance(c, dict) and c.get("ok") is False]
    result: dict[str, Any] = {
        "checks": checks,
        "failed": failed,
        "ok": len(failed) == 0,
        "fixes_applied": fixes_applied,
    }

    next_steps: list[str] = []
    if not checks["python"]["ok"]:
        next_steps.append("Nâng Python lên >= 3.10")
    if not checks["git"]["ok"]:
        next_steps.append("Cài git: winget install Git.Git")
    if not checks["github"]["ok"]:
        hint = checks["github"].get("fix_hint")
        if hint:
            next_steps.append(hint)
    if checks["config"]["target_count"] == 0:
        next_steps.append("cli-fpp target add shop-a --fpp-url http://HOST:81")
    contrib = checks.get("contrib") or {}
    if contrib.get("pending", 0) > 0 and contrib.get("submit_hint"):
        next_steps.append(contrib["submit_hint"])
    if include_target and checks.get("target"):
        next_steps.extend(checks["target"].get("next_steps") or [])

    result["next_steps"] = next_steps

    if check_only and failed:
        result["exit_code"] = 1
    else:
        result["exit_code"] = 0 if result["ok"] else 1

    return result
