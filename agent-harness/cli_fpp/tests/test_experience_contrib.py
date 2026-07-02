"""Tests for experience auto-contribute queue."""

from __future__ import annotations

import json
from unittest.mock import patch

from cli_fpp.core import experience_contrib as contrib


def test_capture_dedupes_and_redacts(tmp_path, monkeypatch):
    queue = tmp_path / "contrib_queue.jsonl"
    monkeypatch.setattr(contrib, "CONTRIB_QUEUE_FILE", queue)
    monkeypatch.setattr(contrib.project, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(contrib, "contrib_enabled", lambda: True)

    first = contrib.capture(
        title="Auth fail",
        body="401 at http://192.168.1.39 with password=secret123",
        scope="global",
    )
    assert first is not None
    assert "192.168" not in first["body"]
    assert "secret" not in first["body"]

    second = contrib.capture(title="Auth fail", body=first["body"], scope="global")
    assert second is None

    status = contrib.queue_status()
    assert status["pending"] == 1


def test_export_marks_pending(tmp_path, monkeypatch):
    queue = tmp_path / "contrib_queue.jsonl"
    state = tmp_path / "contrib_state.json"
    monkeypatch.setattr(contrib, "CONTRIB_QUEUE_FILE", queue)
    monkeypatch.setattr(contrib, "CONTRIB_STATE_FILE", state)
    monkeypatch.setattr(contrib.project, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(contrib, "contrib_enabled", lambda: True)

    contrib.capture(title="Tip", body="Use http not https", scope="global")
    payload = contrib.export_pending(mark_exported=True)
    assert payload["entry_count"] == 1
    lines = [json.loads(ln) for ln in queue.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["status"] == "exported"


def test_submit_to_repo_writes_inbox(tmp_path, monkeypatch):
    queue = tmp_path / "contrib_queue.jsonl"
    state = tmp_path / "contrib_state.json"
    monkeypatch.setattr(contrib, "CONTRIB_QUEUE_FILE", queue)
    monkeypatch.setattr(contrib, "CONTRIB_STATE_FILE", state)
    monkeypatch.setattr(contrib.project, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(contrib, "contrib_enabled", lambda: True)

    repo = tmp_path / "repo"
    (repo / "agent-harness" / "scripts").mkdir(parents=True)
    (repo / "agent-harness" / "scripts" / "build_skill_md.py").write_text("# stub", encoding="utf-8")

    contrib.capture(title="Orange Pi reboot", body="Reboot after rotate persist", scope="device", device_type="orangepi")
    result = contrib.submit_to_repo(repo)
    assert result["submitted"] is True
    inbox = repo / contrib.INBOX_REL
    files = list(inbox.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["schema"] == contrib.SCHEMA_VERSION
    assert data["entry_count"] == 1


def test_contrib_disabled_skips_capture(monkeypatch):
    monkeypatch.setattr(contrib, "contrib_enabled", lambda: False)
    assert contrib.capture(title="X", body="Y") is None
