"""Tests for dev target profile and doctor (mocked SSH/API)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cli_fpp.core import dev_target


def test_target_profile_missing_config():
    with patch("cli_fpp.core.dev_target.project.load_raw_config", return_value={}), patch(
        "cli_fpp.core.dev_target.project.get_active_target_name", return_value=None
    ), patch("cli_fpp.core.dev_target.project.load_config", return_value={}):
        profile = dev_target.target_profile()
    assert profile["complete"] is False
    assert "base_url" in profile["missing"]


def test_save_target_writes_config(tmp_path):
    cfg_path = tmp_path / "config.json"
    with patch("cli_fpp.core.dev_target.project.load_raw_config", return_value={}), patch(
        "cli_fpp.core.dev_target.project.upsert_target",
        return_value={"saved": str(cfg_path), "name": "shop-a", "profile": {}},
    ), patch(
        "cli_fpp.core.dev_target.target_profile",
        return_value={"name": "shop-a", "complete": True},
    ):
        result = dev_target.save_target(
            name="shop-a",
            base_url="http://192.168.1.39:81/",
            username="admin",
            password="secret",
            ssh_host="192.168.1.39",
            ssh_password="orangepi",
        )
    assert result["name"] == "shop-a"


def test_list_targets():
    raw = {
        "default_target": "a",
        "targets": {
            "a": {"base_url": "http://192.168.1.10:81", "username": "u", "password": "p"},
            "b": {"base_url": "http://192.168.1.11:81", "username": "u", "password": "p"},
        },
    }
    with patch("cli_fpp.core.dev_target.project.load_raw_config", return_value=raw), patch(
        "cli_fpp.core.dev_target.project.get_active_target_name", return_value="a"
    ):
        result = dev_target.list_targets()
    assert result["count"] == 2
    assert result["targets"][0]["name"] == "a"
    assert result["targets"][0]["default"] is True


def test_dev_doctor_fpp_not_installed():
    profile = {
        "name": "shop-a",
        "base_url": "http://192.168.1.39:81",
        "username": "admin",
        "password": "x",
        "ssh_host": "192.168.1.39",
        "ssh_password": "y",
        "missing": [],
        "missing_client": [],
        "complete": True,
    }
    conf = MagicMock(host="192.168.1.39")
    fpp_status = {
        "has_compose": False,
        "has_media": False,
        "image_pulled": False,
        "container": {"status": "stopped"},
        "fpp_http": None,
    }

    with patch("cli_fpp.core.dev_target.target_profile", return_value=profile), patch(
        "cli_fpp.core.dev_target.host_ssh.get_ssh_config", return_value=conf
    ), patch("cli_fpp.core.dev_target.host_ssh.run_ssh", return_value="ok"), patch(
        "cli_fpp.core.fpp_docker.fpp_status", return_value=fpp_status
    ), patch(
        "cli_fpp.core.dev_target.fpp_backend.ping",
        side_effect=ConnectionError("refused"),
    ):
        result = dev_target.dev_doctor()

    assert result["fpp_installed"] is False
    assert result["ready"] is False
    assert any("bootstrap" in step for step in result["next_steps"])


def test_dev_doctor_ready():
    profile = {
        "name": "shop-a",
        "base_url": "http://192.168.1.39:81",
        "username": "admin",
        "password": "x",
        "ssh_host": "192.168.1.39",
        "ssh_password": "y",
        "missing": [],
        "missing_client": [],
        "complete": True,
    }
    conf = MagicMock(host="192.168.1.39")
    fpp_status = {
        "has_compose": True,
        "has_media": True,
        "image_pulled": True,
        "container": {"status": "running"},
        "fpp_http": "ok",
    }

    with patch("cli_fpp.core.dev_target.target_profile", return_value=profile), patch(
        "cli_fpp.core.dev_target.host_ssh.get_ssh_config", return_value=conf
    ), patch(
        "cli_fpp.core.dev_target.host_ssh.run_ssh",
        side_effect=lambda cmd, **_: "ok" if cmd.strip() == "echo ok" else "Docker version 24",
    ), patch(
        "cli_fpp.core.fpp_docker.fpp_status", return_value=fpp_status
    ), patch("cli_fpp.core.dev_target.fpp_backend.ping", return_value={"ok": True}):
        result = dev_target.dev_doctor()

    assert result["fpp_installed"] is True
    assert result["ready"] is True
