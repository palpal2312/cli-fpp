"""Tests for FPP Docker dev module (no live SSH)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli_fpp.core import fpp_docker


def test_resolve_fpp_source_explicit(tmp_path: Path):
    (tmp_path / "src" / "channeloutput").mkdir(parents=True)
    (tmp_path / "src" / "channeloutput" / "FBMatrix.cpp").write_text("// x")
    root = fpp_docker.resolve_fpp_source(tmp_path)
    assert root == tmp_path.resolve()


def test_resolve_fpp_source_missing(tmp_path: Path):
    with pytest.raises(ValueError, match="Not an FPP source"):
        fpp_docker.resolve_fpp_source(tmp_path)


def test_render_compose_yaml():
    yml = fpp_docker.render_compose_yaml(host_ip="192.168.1.39", http_port=81)
    assert "falconchristmas/fpp:latest" in yml
    assert "/dev/fb0" in yml
    assert "192.168.1.39:81:80/tcp" in yml


def test_virtual_matrix_set_merge():
    co = {
        "channelOutputs": [
            {
                "type": "VirtualMatrix",
                "width": 1920,
                "height": 1080,
                "invert": False,
                "flipHorizontal": False,
            }
        ]
    }

    def fake_run(cmd, **kwargs):
        if cmd.startswith("cat "):
            return json.dumps(co)
        return ""

    with patch("cli_fpp.core.fpp_docker.host_ssh.run_ssh", side_effect=fake_run), patch(
        "cli_fpp.core.fpp_docker.write_host_text"
    ) as mock_write, patch(
        "cli_fpp.core.fpp_docker._sync_config_to_container"
    ), patch(
        "cli_fpp.core.fpp_docker.host_ssh.restart_fpp_container",
        return_value={"container": "fpp-docker"},
    ), patch(
        "cli_fpp.core.fpp_docker.host_ssh.get_ssh_config",
        return_value=object(),
    ), patch(
        "cli_fpp.core.fpp_docker.host_ssh.detect_compose_dir",
        return_value="/home/orangepi/fpp/Docker",
    ):
        result = fpp_docker.virtual_matrix_set(rotate=90, invert=True, restart_container=True)
    assert result["virtual_matrix"]["rotate"] == 90
    assert result["virtual_matrix"]["invert"] is True
    assert mock_write.called
    written = mock_write.call_args[0][1]
    data = json.loads(written)
    assert data["channelOutputs"][0]["channelCount"] == 1920 * 1080 * 3


def test_fpp_bootstrap_workflow(tmp_path: Path):
    root = tmp_path / "fpp"
    (root / "src").mkdir(parents=True)
    (root / "www").mkdir()

    conf = MagicMock(host="192.168.1.39")
    doctor_before = {"ready": False, "fpp_installed": False}
    doctor_after = {"ready": True, "fpp_installed": True}

    with patch("cli_fpp.core.fpp_docker.host_ssh.get_ssh_config", return_value=conf), patch(
        "cli_fpp.core.dev_target.dev_doctor", side_effect=[doctor_before, doctor_after]
    ) as mock_doctor, patch(
        "cli_fpp.core.fpp_docker.upload_fpp_source_tree",
        return_value={"source": str(root), "remote_dir": "/home/orangepi/fpp/Docker/fpp"},
    ), patch(
        "cli_fpp.core.fpp_docker.fpp_install",
        return_value={"installed": True},
    ), patch(
        "cli_fpp.core.fpp_docker.fpp_build",
        return_value={"built": True},
    ), patch(
        "cli_fpp.core.fpp_docker.host_ssh.restart_fpp_container",
        return_value={"container": "fpp-docker"},
    ), patch(
        "cli_fpp.core.fpp_docker.resolve_fpp_source", return_value=root
    ):
        result = fpp_docker.fpp_bootstrap(source=root, conf=conf)

    assert result["ready"] is True
    assert mock_doctor.call_count == 2
    assert any("upload_source" in step for step in result["steps"])

