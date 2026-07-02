"""Tests for target briefing and FPP version audit."""

from __future__ import annotations

from unittest.mock import patch

from cli_fpp.core import target_setup


def test_parse_fpp_version_dict():
    assert target_setup.parse_fpp_version({"Version": "8.0"}) == "8.0"
    assert target_setup.parse_fpp_version("8.1-beta") == "8.1-beta"


def test_check_fpp_version_api():
    profile = {
        "base_url": "http://192.168.1.39:81",
        "username": "admin",
        "password": "x",
    }
    with patch(
        "cli_fpp.core.target_setup.fpp_backend.api_get",
        return_value={"Version": "8.2"},
    ):
        result = target_setup.check_fpp_version("shop-a", profile=profile)
    assert result["ok"] is True
    assert result["version"] == "8.2"
    assert result["source"] == "api/fppd/version"


def test_check_fpp_version_missing_config():
    result = target_setup.check_fpp_version(
        "x",
        profile={"base_url": "", "username": "", "password": ""},
    )
    assert result["ok"] is False
    assert "Thiếu cấu hình" in (result.get("error") or "")


def test_audit_all_targets():
    listing = {
        "count": 2,
        "default_target": "a",
        "active_target": "a",
        "targets": [
            {"name": "a", "profile": {"base_url": "http://a", "username": "u", "password": "p"}},
            {"name": "b", "profile": {"base_url": "http://b", "username": "u", "password": "p"}},
        ],
    }
    with patch("cli_fpp.core.target_setup.dev_target.list_targets", return_value=listing), patch(
        "cli_fpp.core.target_setup.project.get_target_profile",
        side_effect=lambda name, **_: {
            "base_url": f"http://{name}",
            "username": "admin",
            "password": "x",
        },
    ), patch(
        "cli_fpp.core.target_setup.check_fpp_version",
        side_effect=lambda name, **_: {"name": name, "ok": True, "version": "8.0", "reachable": True},
    ):
        audit = target_setup.audit_all_targets()
    assert audit["target_count"] == 2
    assert audit["version_ok_count"] == 2
    assert len(audit["checks"]) == 2


def test_format_briefing_text():
    text = target_setup.format_briefing_text(
        {
            "briefing": {"target_count": 1, "target_names": ["shop-a"]},
            "audit": {
                "checks": [
                    {"name": "shop-a", "version": "8.0", "ok": True},
                ]
            },
        }
    )
    assert "1 target-device" in text
    assert "shop-a" in text and "8.0" in text


def test_run_setup_non_interactive_audit_only():
    with patch(
        "cli_fpp.core.target_setup.target_briefing",
        return_value={"target_count": 1, "target_names": ["a"]},
    ), patch(
        "cli_fpp.core.target_setup.audit_all_targets",
        return_value={"target_count": 1, "checks": []},
    ):
        data = target_setup.run_setup(interactive=False, skip_add_prompt=True)
    assert data["briefing"]["target_count"] == 1
    assert "audit" in data
