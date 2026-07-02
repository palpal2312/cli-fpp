"""Tests for agent_tools facade."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cli_fpp.core import agent_tools


def test_tool_schema_has_core_tools():
    names = {t["name"] for t in agent_tools.tool_schema()}
    assert "cli_fpp_list_targets" in names
    assert "cli_fpp_suggest" in names
    assert "cli_fpp_upload_media" in names
    assert "cli_fpp_play_playlist" in names
    assert len(names) >= 6


def test_list_targets_delegates():
    with patch.object(agent_tools.dev_target, "list_targets", return_value={"count": 1}) as mock:
        out = agent_tools.list_targets()
    assert out["count"] == 1
    mock.assert_called_once()


def test_suggest_delegates():
    with patch.object(agent_tools.guide, "suggest", return_value={"understood": True}) as mock:
        out = agent_tools.suggest("play test")
    assert out["understood"] is True
    mock.assert_called_once_with("play test", target_name=None)


def test_play_playlist_uses_base_url():
    with patch.object(agent_tools.project, "set_active_target"), patch.object(
        agent_tools.project, "get_connection", return_value="http://fpp.local:81"
    ), patch.object(agent_tools.playlist, "play", return_value={"ok": True}) as mock:
        agent_tools.play_playlist("Holiday", repeat=True, target_name="shop-a")
    mock.assert_called_once_with("Holiday", repeat=True, base_url="http://fpp.local:81")


def test_dispatch_tool_unknown():
    try:
        agent_tools.dispatch_tool("nope", {})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unknown tool" in str(exc)
