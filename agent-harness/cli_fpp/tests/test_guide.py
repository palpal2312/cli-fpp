"""Tests for guide / suggest / display preference."""

from __future__ import annotations

import pytest

from cli_fpp.core import guide


class TestDisplayPreference:
    def test_json_hint(self):
        assert guide.parse_display_preference("cho tôi json")["format"] == "json"

    def test_brief_hint(self):
        assert guide.parse_display_preference("trạng thái tóm tắt")["detail"] == "brief"


class TestSuggest:
    def test_play_playlist(self):
        r = guide.suggest('play playlist "Holiday" lặp lại')
        assert r["understood"] is True
        assert "experiences" in r
        assert "global" in r["experiences"]
        assert r["interpreted_intent"] == "play_playlist"
        assert r["confirmation_required"] is True
        assert "Holiday" in r["proposed_cli"][0]
        assert "--repeat" in r["proposed_cli"][0]

    def test_status(self):
        r = guide.suggest("FPP đang chạy gì, hiển thị json")
        assert r["understood"] is True
        assert r["interpreted_intent"] == "system_status"
        assert r["confirmation_required"] is False
        assert "player status" in r["proposed_cli"][0]

    def test_upload_media(self):
        r = guide.suggest("upload ảnh này lên FPP")
        assert r["understood"] is True
        assert r["interpreted_intent"] == "upload_media"
        assert r["cli_scope"] == "client"
        assert r["confirmation_required"] is True
        assert "media propose" in r["proposed_cli"][0]
        assert "media upload" in r["proposed_cli"][1]
        assert len(r["agent_workflow"]) >= 4

    def test_rotate_display_dev(self):
        r = guide.suggest("xoay màn portrait trên Orange Pi")
        assert r["understood"] is True
        assert r["interpreted_intent"] == "rotate_display"
        assert r["cli_scope"] == "dev"
        assert any("dev host display" in c for c in r["proposed_cli"])

    def test_upload_beats_rotate(self):
        r = guide.suggest("upload ảnh portrait lên FPP")
        assert r["interpreted_intent"] == "upload_media"
        assert r["cli_scope"] == "client"

    def test_fpp_autostart_dev(self):
        r = guide.suggest("cài fpp docker autostart khi boot")
        assert r["cli_scope"] == "dev"
        assert r["interpreted_intent"] == "fpp_autostart"

    def test_fpp_deploy_dev(self):
        r = guide.suggest("deploy patch FPP lên Orange Pi")
        assert r["cli_scope"] == "dev"
        assert r["interpreted_intent"] == "fpp_deploy"
        assert any("dev fpp deploy" in c for c in r["proposed_cli"])

    def test_fpp_bootstrap_dev(self):
        r = guide.suggest("target chưa cài fpp docker, bootstrap lần đầu")
        assert r["cli_scope"] == "dev"
        assert r["interpreted_intent"] == "fpp_bootstrap"
        assert any("dev fpp bootstrap" in c for c in r["proposed_cli"])

    def test_multi_target_client(self):
        r = guide.suggest("cli-fpp target list các máy FPP")
        assert r["understood"] is False or "target" in str(r).lower()

    def test_classify_cli_scope(self):
        assert guide.classify_cli_scope("play playlist test") == "client"
        assert guide.classify_cli_scope("xoay màn hdmi") == "dev"

    def test_unknown(self):
        r = guide.suggest("làm bánh chưng")
        assert r["understood"] is False
        assert "cli_scope" in r
        assert "suggested_topics" in r


class TestGuide:
    def test_topics(self):
        assert "playlist" in guide.list_topics()

    def test_get_guide(self):
        g = guide.get_guide("playlist")
        assert "web_ui" in g
        assert "cli" in g

    def test_media_upload_guide(self):
        g = guide.get_guide("media_upload")
        cli_text = " ".join(g["cli"]).lower()
        assert "media propose" in cli_text
        assert "media upload" in cli_text

    def test_dev_guide(self):
        g = guide.get_guide("dev")
        cli_text = " ".join(g["cli"]).lower()
        assert "dev host display" in cli_text

    def test_unknown_topic(self):
        with pytest.raises(ValueError, match="Unknown topic"):
            guide.get_guide("nope")
