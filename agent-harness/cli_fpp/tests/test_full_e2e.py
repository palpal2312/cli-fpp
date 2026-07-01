"""E2E tests — require a live FPP instance at FPP_BASE_URL."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
import requests

BASE = os.environ.get("FPP_BASE_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(
    not BASE,
    reason="Set FPP_BASE_URL to run E2E tests against a real FPP instance",
)


def _resolve_cli():
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which("cli-fpp")
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError("cli-fpp not in PATH. Install with: pip install -e .")
    print("[_resolve_cli] Falling back to: python -m cli_fpp")
    return [sys.executable, "-m", "cli_fpp"]


CLI_BASE = _resolve_cli()


def _run(args, check=True):
    return subprocess.run(
        CLI_BASE + ["--url", BASE] + args,
        capture_output=True,
        text=True,
        check=check,
    )


class TestConnectivity:
    def test_ping_http(self):
        resp = requests.get(f"{BASE}/api/system/status", timeout=15)
        resp.raise_for_status()

    def test_cli_ping_json(self):
        result = _run(["--json", "ping"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)


class TestSystem:
    def test_system_status(self):
        result = _run(["system", "status", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_fppd_version(self):
        result = _run(["system", "version", "--json"])
        assert result.returncode == 0


class TestPlaylist:
    def test_list_playlists(self):
        result = _run(["playlist", "list", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)


class TestCommands:
    def test_list_commands(self):
        result = _run(["command", "list", "--json"])
        assert result.returncode == 0
