"""Tests for host SSH display module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cli_fpp.core import host_ssh


def test_rotate_map():
    assert host_ssh.ROTATE_MAP["landscape"] == 0
    assert host_ssh.ROTATE_MAP["portrait-right"] == 1
    assert host_ssh.ROTATE_MAP["portrait-left"] == 3


def test_set_video_rotate_portrait():
    out = host_ssh._set_video_rotate("cma=128M", 90)
    assert "video=HDMI-A-1:1920x1080M@60,rotate=90" in out
    assert "cma=128M" in out


def test_set_video_rotate_landscape():
    out = host_ssh._set_video_rotate("cma=128M video=HDMI-A-1:1920x1080M@60,rotate=90", 0)
    assert "rotate=" not in out


@patch("cli_fpp.core.host_ssh.try_modetest_rotate")
@patch("cli_fpp.core.host_ssh.apply_boot_rotation")
@patch("cli_fpp.core.host_ssh.run_ssh")
@patch("cli_fpp.core.host_ssh.get_ssh_config")
def test_display_rotate(mock_conf, mock_run, mock_boot, mock_modetest):
    mock_conf.return_value = host_ssh.SSHConfig("192.168.1.39", "orangepi", "x")
    mock_run.return_value = ""
    mock_boot.return_value = {"extraargs": "video=...,rotate=90", "reboot_required": True}
    mock_modetest.return_value = {"attempted": True, "ok": False}
    with patch("cli_fpp.core.host_ssh.display_status") as mock_status:
        mock_status.return_value = {"orientation": "portrait-right", "fb_rotate": 1}
        result = host_ssh.display_rotate("portrait-right")
    assert result["applied"]["fb_rotate"] == 1
    assert result["applied"]["boot_degrees"] == 90
    mock_boot.assert_called_once()


@patch("cli_fpp.core.host_ssh.try_modetest_rotate")
@patch("cli_fpp.core.host_ssh.apply_boot_rotation")
@patch("cli_fpp.core.host_ssh.run_ssh_batch")
@patch("cli_fpp.core.host_ssh.display_status")
@patch("cli_fpp.core.host_ssh.get_ssh_config")
def test_install_persist(mock_conf, mock_status, mock_batch, mock_boot, mock_modetest):
    mock_conf.return_value = host_ssh.SSHConfig("192.168.1.39", "orangepi", "x")
    mock_status.return_value = {"orientation": "portrait-right"}
    mock_boot.return_value = {"reboot_required": True}
    mock_modetest.return_value = {"attempted": True, "ok": False}
    result = host_ssh.install_display_persist("portrait-right")
    assert result["persist"]["fb_rotate"] == 1
    mock_batch.assert_called_once()


@patch("cli_fpp.core.host_ssh.run_ssh_batch")
@patch("cli_fpp.core.host_ssh.fpp_autostart_status")
@patch("cli_fpp.core.host_ssh.detect_compose_dir")
@patch("cli_fpp.core.host_ssh.get_ssh_config")
def test_install_fpp_autostart(mock_conf, mock_dir, mock_status, mock_batch):
    mock_conf.return_value = host_ssh.SSHConfig("192.168.1.39", "orangepi", "x")
    mock_dir.return_value = "/home/orangepi/fpp/Docker"
    mock_status.return_value = {"ready": True}
    result = host_ssh.install_fpp_autostart()
    assert result["installed"] is True
    mock_batch.assert_called_once()
