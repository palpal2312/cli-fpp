"""Tests for generated OpenAPI registry."""

from __future__ import annotations

from unittest.mock import patch

from cli_fpp.core.openapi_registry import OPERATIONS, execute, tags


BASE = "http://fpp.local"


class TestOpenAPIRegistry:
    def test_all_operations_registered(self):
        assert len(OPERATIONS) == 253

    def test_tags_count(self):
        assert len(tags()) >= 38

    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_execute_get(self, mock_get):
        mock_get.return_value = {"ok": True}
        result = execute("player__get-status", base_url=BASE)
        assert result == {"ok": True}
        mock_get.assert_called_once_with("/api/player/status", base_url=BASE, params=None)

    @patch("cli_fpp.utils.fpp_backend.api_get")
    def test_execute_wildcard_path(self, mock_get):
        execute(
            "configfile__get",
            path_values={"_wildcard": "gpio.json"},
            base_url=BASE,
        )
        args, _ = mock_get.call_args
        assert args[0] == "/api/configfile/gpio.json"
