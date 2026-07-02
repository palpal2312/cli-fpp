"""Unit tests — HTTP calls mocked."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cli_fpp.core import commands, playlist, project
from cli_fpp.utils import fpp_backend

BASE = "http://fpp.local"


def mock_response(status_code: int = 200, json_data=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"Content-Type": "application/json"}
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text or json.dumps(json_data if json_data is not None else {})
    resp.raise_for_status = MagicMock()
    return resp


class TestBackend:
    def test_url_construction(self):
        assert fpp_backend._url(BASE, "/api/playlists") == f"{BASE}/api/playlists"

    def test_url_missing_base(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="base URL not configured"):
                fpp_backend._url("", "/api/playlists")

    def test_command_path(self):
        path = fpp_backend.command_path("Start Playlist", "My Show", "1", "true")
        assert path.startswith("/api/command/")
        assert "My%20Show" in path

    @patch("cli_fpp.utils.fpp_backend.requests.request")
    def test_api_get(self, mock_req):
        mock_req.return_value = mock_response(200, ["A", "B"])
        result = fpp_backend.api_get("/api/playlists", base_url=BASE)
        assert result == ["A", "B"]

    @patch("cli_fpp.utils.fpp_backend.requests.request")
    def test_api_post(self, mock_req):
        mock_req.return_value = mock_response(200, {"ok": True})
        result = fpp_backend.api_post("/api/command", {"command": "x"}, base_url=BASE)
        assert result == {"ok": True}

    @patch("cli_fpp.utils.fpp_backend.requests.request")
    def test_api_delete_204(self, mock_req):
        mock_req.return_value = mock_response(204)
        assert fpp_backend.api_delete("/api/x", base_url=BASE) == {}


class TestProject:
    def test_get_connection_normalizes_scheme(self):
        with patch.dict("os.environ", {"FPP_BASE_URL": "192.168.1.10"}, clear=False):
            assert project.get_connection() == "http://192.168.1.10"

    def test_get_connection_explicit(self):
        assert project.get_connection("http://fpp.test") == "http://fpp.test"


class TestPlaylist:
    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_list_playlists(self, mock_get):
        mock_get.return_value = ["Show1", "Show2"]
        assert playlist.list_playlists(base_url=BASE) == ["Show1", "Show2"]

    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_play_repeat(self, mock_get):
        playlist.play("Holiday", start_item=2, repeat=True, base_url=BASE)
        args, kwargs = mock_get.call_args
        assert "Holiday" in args[0]
        assert "true" in args[0]

    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_stop_now(self, mock_get):
        playlist.stop(graceful=False, base_url=BASE)
        args, _ = mock_get.call_args
        assert args[0] == "/api/playlists/stop"

    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_stop_graceful(self, mock_get):
        playlist.stop(graceful=True, base_url=BASE)
        args, _ = mock_get.call_args
        assert args[0] == "/api/playlists/stopgracefully"


class TestCommands:
    @patch("cli_fpp.utils.fpp_backend.api_post")
    def test_run_with_args(self, mock_post):
        commands.run("Volume Set", ["80"], base_url=BASE)
        mock_post.assert_called_once()
        assert mock_post.call_args[0][0] == "/api/command/Volume%20Set"

    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_trigger_preset_slot(self, mock_get):
        commands.trigger_preset("3", base_url=BASE)
        args, _ = mock_get.call_args
        assert "Trigger%20Command%20Preset%20Slot" in args[0] or "Slot" in args[0]


class TestSystem:
    @patch("cli_fpp.utils.fpp_backend.api_post")
    def test_volume_set(self, mock_post):
        from cli_fpp.core import system

        system.volume_set(70, base_url=BASE)
        mock_post.assert_called_once_with("/api/system/volume", {"volume": 70}, base_url=BASE)


class TestSequence:
    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_toggle_pause(self, mock_get):
        from cli_fpp.core import sequence

        sequence.toggle_pause(base_url=BASE)
        args, _ = mock_get.call_args
        assert args[0] == "/api/sequence/current/togglePause"
