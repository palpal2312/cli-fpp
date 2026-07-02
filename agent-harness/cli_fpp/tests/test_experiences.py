"""Tests for layered experience memory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cli_fpp.core import experiences


def test_layers_separate_global_device_player():
    with patch(
        "cli_fpp.core.experiences.get_context",
        return_value={
            "target_name": "shop-a",
            "device_type": "orangepi",
            "device_label": "Orange Pi",
            "player_line": "8.x",
            "player_version": "8.2",
        },
    ):
        result = experiences.list_experiences()
    layers = result["layers"]
    assert layers["global"]["count"] >= 1
    assert any(e["scope"] == "global" for e in layers["global"]["entries"])
    device_titles = [e["title"] for e in layers["device"]["entries"]]
    assert any("RK356x" in t or "reboot" in t.lower() for t in device_titles)
    for entry in layers["device"]["entries"]:
        assert entry["scope_label"] == "Kinh nghiệm riêng Target (thiết bị)"
        assert entry["matches_context"] is True
    for entry in layers["global"]["entries"]:
        assert entry["scope_label"] == "Kinh nghiệm chung"
        assert "luôn áp dụng" in entry["match_reason"].lower()


def test_suggest_experiences_structured():
    with patch(
        "cli_fpp.core.experiences.list_experiences",
        return_value={
            "priority_hint": experiences.PRIORITY_HINT,
            "context": {},
            "layers": {
                "global": {"entries": [{"id": "g1", "scope": "global", "scope_label": "Kinh nghiệm chung", "applies_to": "Mọi target", "match_reason": "x", "title": "G", "body": "b"}]},
                "device": {"entries": []},
                "player": {"entries": []},
            },
        },
    ):
        out = experiences.experiences_for_suggest()
    assert "global" in out
    assert "device_specific" in out
    assert "player_specific" in out
    assert out["global"][0]["scope_label"] == "Kinh nghiệm chung"


def test_remember_device_scope(tmp_path):
    exp_file = tmp_path / "experiences.json"
    with patch.object(experiences, "EXPERIENCES_FILE", exp_file), patch(
        "cli_fpp.core.experiences.get_context",
        return_value={"target_name": "x", "device_type": "orangepi", "player_line": None},
    ):
        out = experiences.remember_experience("Only for orangepi board", scope="device")
    assert out["entry"]["scope"] == "device"
    assert out["entry"]["applies_to"].startswith("Target device_type=orangepi")


def test_add_player_requires_version():
    with pytest.raises(ValueError, match="player-line"):
        experiences.add_experience(title="T", body="B", scope="player")
