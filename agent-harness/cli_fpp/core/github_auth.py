"""GitHub authentication — multi-tier: env → gh CLI (ClaudeKit-style)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Literal

AuthMethod = Literal["env", "gh-cli", "none"]

MIN_GH_VERSION = (2, 20, 0)
GH_COMMAND_TIMEOUT = 10

_token_cache: str | None = None
_token_method: AuthMethod | None = None
_gh_installed_cache: bool | None = None


class GitHubAuthError(RuntimeError):
    """Raised when GitHub auth is required but unavailable."""


@dataclass
class TokenResult:
    token: str
    method: AuthMethod


@dataclass
class GhStatus:
    installed: bool
    version: str | None
    version_ok: bool
    authenticated: bool
    username: str | None
    host: str
    scopes: list[str]
    active: bool
    raw: str
    error: str | None = None


def _run(
    args: list[str],
    *,
    timeout: int = GH_COMMAND_TIMEOUT,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    )


def parse_version(version_line: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_line)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def version_at_least(current: tuple[int, int, int], minimum: tuple[int, int, int]) -> bool:
    return current >= minimum


def is_gh_installed() -> bool:
    global _gh_installed_cache
    if _gh_installed_cache is not None:
        return _gh_installed_cache
    _gh_installed_cache = shutil.which("gh") is not None
    return _gh_installed_cache


def get_gh_version() -> str | None:
    if not is_gh_installed():
        return None
    try:
        proc = _run(["gh", "--version"])
        if proc.returncode != 0:
            return None
        return (proc.stdout or proc.stderr or "").splitlines()[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def gh_version_ok() -> bool:
    line = get_gh_version()
    if not line:
        return False
    parsed = parse_version(line)
    return bool(parsed and version_at_least(parsed, MIN_GH_VERSION))


def get_token_from_env() -> str | None:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return None


def get_token_from_gh_cli() -> str | None:
    if not is_gh_installed():
        return None
    for args in (["gh", "auth", "token", "-h", "github.com"], ["gh", "auth", "token"]):
        try:
            proc = _run(args)
            if proc.returncode == 0:
                token = (proc.stdout or "").strip()
                if token:
                    return token
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


def get_token(*, use_cache: bool = True) -> TokenResult:
    """Priority: GITHUB_TOKEN/GH_TOKEN → gh auth token."""
    global _token_cache, _token_method
    if use_cache and _token_cache and _token_method:
        return TokenResult(token=_token_cache, method=_token_method)

    env_token = get_token_from_env()
    if env_token:
        _token_cache = env_token
        _token_method = "env"
        return TokenResult(token=env_token, method="env")

    gh_token = get_token_from_gh_cli()
    if gh_token:
        _token_cache = gh_token
        _token_method = "gh-cli"
        return TokenResult(token=gh_token, method="gh-cli")

    raise GitHubAuthError(_auth_help_message())


def clear_token_cache() -> None:
    global _token_cache, _token_method, _gh_installed_cache
    _token_cache = None
    _token_method = None
    _gh_installed_cache = None


def auth_status(*, host: str = "github.com") -> GhStatus:
    if not is_gh_installed():
        return GhStatus(
            installed=False,
            version=None,
            version_ok=False,
            authenticated=False,
            username=None,
            host=host,
            scopes=[],
            active=False,
            raw="",
            error="GitHub CLI (gh) chưa cài",
        )

    version_line = get_gh_version()
    parsed = parse_version(version_line or "")
    version_ok = bool(parsed and version_at_least(parsed, MIN_GH_VERSION))

    try:
        proc = _run(["gh", "auth", "status", "-h", host])
        raw = ((proc.stdout or "") + (proc.stderr or "")).strip()
        authenticated = proc.returncode == 0 and "Logged in" in raw
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GhStatus(
            installed=True,
            version=version_line,
            version_ok=version_ok,
            authenticated=False,
            username=None,
            host=host,
            scopes=[],
            active=False,
            raw="",
            error=str(exc),
        )

    username = None
    m_user = re.search(r"Logged in to github\.com account (\S+)", raw)
    if m_user:
        username = m_user.group(1)

    scopes: list[str] = []
    m_scopes = re.search(r"Token scopes: '([^']*)'", raw)
    if m_scopes and m_scopes.group(1):
        scopes = [s.strip() for s in m_scopes.group(1).split(",") if s.strip()]

    active = "Active account: true" in raw

    return GhStatus(
        installed=True,
        version=version_line,
        version_ok=version_ok,
        authenticated=authenticated,
        username=username,
        host=host,
        scopes=scopes,
        active=active,
        raw=raw,
    )


def get_github_username(*, token: str | None = None) -> str | None:
    if not is_gh_installed():
        return None
    try:
        args = ["gh", "api", "user", "-q", ".login"]
        env = os.environ.copy()
        if token:
            env["GH_TOKEN"] = token
        proc = subprocess.run(args, capture_output=True, text=True, timeout=GH_COMMAND_TIMEOUT, env=env)
        if proc.returncode == 0:
            login = (proc.stdout or "").strip()
            return login or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return auth_status().username


def login(*, host: str = "github.com", web: bool = True) -> dict[str, Any]:
    """Run gh auth login (interactive)."""
    if not is_gh_installed():
        raise GitHubAuthError(
            "Chưa cài GitHub CLI.\n"
            "Windows: winget install GitHub.cli\n"
            "macOS: brew install gh\n"
            "Linux: sudo apt install gh"
        )
    clear_token_cache()
    args = ["gh", "auth", "login", "-h", host]
    if web:
        args.extend(["-p", "https", "-w"])
    proc = subprocess.run(args, timeout=600)
    if proc.returncode != 0:
        raise GitHubAuthError("gh auth login thất bại")
    status = auth_status(host=host)
    return {
        "ok": status.authenticated,
        "username": status.username,
        "host": host,
        "hint": "Chọn 'Login with a web browser' khi được hỏi",
    }


def run_gh_api(
    method: str,
    endpoint: str,
    *,
    token: str | None = None,
    input_json: dict[str, Any] | None = None,
) -> Any:
    """Call GitHub REST via gh api."""
    token = token or get_token().token
    args = ["gh", "api", "-X", method.upper(), endpoint]
    if input_json is not None:
        args.extend(["--input", "-"])
        payload = json.dumps(input_json)
        proc = subprocess.run(
            args,
            input=payload,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "GH_TOKEN": token},
        )
    else:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "GH_TOKEN": token},
        )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "gh api failed").strip()
        raise GitHubAuthError(err)
    out = (proc.stdout or "").strip()
    if not out:
        return {}
    return json.loads(out)


def ensure_fork(upstream: str, *, token: str | None = None) -> str:
    """Ensure fork exists; return fork full name owner/repo."""
    token = token or get_token().token
    if "/" not in upstream:
        raise ValueError("upstream phải dạng owner/repo")
    owner, repo = upstream.split("/", 1)
    user = get_github_username(token=token)
    if not user:
        raise GitHubAuthError("Không lấy được GitHub username")

    fork_full = f"{user}/{repo}"
    if fork_full.lower() == upstream.lower():
        return fork_full

    try:
        run_gh_api("GET", f"repos/{fork_full}", token=token)
        return fork_full
    except GitHubAuthError:
        pass

    subprocess.run(
        ["gh", "repo", "fork", upstream, "--clone=false"],
        check=True,
        timeout=120,
        env={**os.environ, "GH_TOKEN": token},
    )
    return fork_full


def gh_upgrade_hint() -> str:
    if sys.platform == "win32":
        return "winget upgrade GitHub.cli"
    if sys.platform == "darwin":
        return "brew upgrade gh"
    return "sudo apt update && sudo apt upgrade gh  # hoặc https://cli.github.com"


def _auth_help_message() -> str:
    return (
        "Chưa có GitHub authentication.\n\n"
        "Cách 1 (khuyến nghị): GitHub CLI\n"
        "  winget install GitHub.cli   # Windows\n"
        "  gh auth login -h github.com   # chọn Login with a web browser\n\n"
        "Cách 2: biến môi trường\n"
        "  set GITHUB_TOKEN=ghp_...\n\n"
        "Kiểm tra: cli-fpp doctor"
    )


def diagnostic() -> dict[str, Any]:
    status = auth_status()
    token_ok = False
    token_method: AuthMethod | None = None
    try:
        tr = get_token(use_cache=False)
        token_ok = bool(tr.token)
        token_method = tr.method
    except GitHubAuthError as exc:
        return {
            "gh": {
                "installed": status.installed,
                "version": status.version,
                "version_ok": status.version_ok,
                "authenticated": status.authenticated,
                "username": status.username,
                "scopes": status.scopes,
            },
            "token_ok": False,
            "token_method": None,
            "error": str(exc),
            "upgrade_hint": gh_upgrade_hint() if status.installed and not status.version_ok else None,
        }
    return {
        "gh": {
            "installed": status.installed,
            "version": status.version,
            "version_ok": status.version_ok,
            "authenticated": status.authenticated,
            "username": status.username or get_github_username(token=tr.token if token_ok else None),
            "scopes": status.scopes,
        },
        "token_ok": token_ok,
        "token_method": token_method,
    }
