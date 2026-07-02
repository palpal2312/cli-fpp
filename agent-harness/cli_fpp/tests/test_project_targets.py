"""Tests for multi-target config registry."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cli_fpp.core import project


def test_migrate_flat_to_targets():
    raw = {
        "base_url": "http://192.168.1.39:81",
        "username": "admin",
        "password": "secret",
        "ssh_host": "192.168.1.39",
    }
    migrated = project._migrate_flat_to_targets(raw)
    assert migrated["targets"]["default"]["base_url"] == "http://192.168.1.39:81"
    assert migrated["default_target"] == "default"


def test_upsert_and_list_targets(tmp_path):
    cfg_file = tmp_path / "config.json"
    with patch.object(project, "CONFIG_FILE", cfg_file), patch.object(
        project, "CONFIG_DIR", tmp_path
    ), patch.dict("os.environ", {}, clear=True):
        project.set_active_target(None)
        project.upsert_target(
            "shop-a",
            {
                "base_url": "http://192.168.1.10:81",
                "username": "admin",
                "password": "x",
            },
            make_default=True,
        )
        project.upsert_target(
            "shop-b",
            {"base_url": "http://192.168.1.11:81", "username": "admin", "password": "y"},
        )
        names = project.list_target_names()
        assert names == ["shop-a", "shop-b"]

        project.set_active_target("shop-b")
        cfg = project.load_config()
        assert cfg["base_url"] == "http://192.168.1.11:81"
        assert cfg["_target"] == "shop-b"


def test_set_default_target(tmp_path):
    cfg_file = tmp_path / "config.json"
    with patch.object(project, "CONFIG_FILE", cfg_file), patch.object(
        project, "CONFIG_DIR", tmp_path
    ):
        project.upsert_target("a", {"base_url": "http://a"}, make_default=True)
        project.upsert_target("b", {"base_url": "http://b"})
        project.set_default_target("b")
        raw = project.load_raw_config()
        assert raw["default_target"] == "b"
        assert raw["base_url"] == "http://b"


def test_remove_target(tmp_path):
    cfg_file = tmp_path / "config.json"
    with patch.object(project, "CONFIG_FILE", cfg_file), patch.object(
        project, "CONFIG_DIR", tmp_path
    ):
        project.upsert_target("a", {"base_url": "http://a"}, make_default=True)
        project.upsert_target("b", {"base_url": "http://b"})
        project.remove_target("a")
        assert project.list_target_names() == ["b"]
        assert project.load_raw_config()["default_target"] == "b"


def test_validate_target_name():
    assert project.validate_target_name("shop-a") == "shop-a"
    with pytest.raises(ValueError):
        project.validate_target_name("9bad")
