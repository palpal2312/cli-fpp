"""Tests for campaign intent and experience suggest overrides."""

from __future__ import annotations

from cli_fpp.core import guide


class TestCampaignIntent:
    def test_run_campaign_banner_tet(self):
        r = guide.suggest("chạy banner Tết trên cửa hàng")
        assert r["understood"] is True
        assert r["interpreted_intent"] == "run_campaign"
        assert r["confirmation_required"] is True
        assert "media propose" in " ".join(r["proposed_cli"])
        assert "Tết" in r["proposed_cli"][3]
        assert "experiences" in r

    def test_campaign_guide_topic(self):
        g = guide.get_guide("campaign")
        assert "playlist play" in " ".join(g["cli"]).lower()


class TestSuggestOverride:
    def test_limonade_overrides_system_status(self):
        r = guide.suggest("FPP đang chạy gì, hiển thị json")
        assert r["understood"] is True
        assert r["interpreted_intent"] == "system_status"
        assert "player status" in r["proposed_cli"][0]
        assert r.get("experience_override_applied") == "global.limonade-system-status"
