"""Tests for target/player classification."""

from __future__ import annotations

import pytest

from cli_fpp.core import target_catalog


def test_normalize_device_type():
    assert target_catalog.normalize_device_type("Orange Pi") == "orangepi"
    assert target_catalog.normalize_device_type("rpi") == "raspberrypi"
    with pytest.raises(ValueError):
        target_catalog.normalize_device_type("atari")


def test_infer_device_type_from_ssh_user():
    assert target_catalog.infer_device_type({"ssh_user": "orangepi"}) == "orangepi"
    assert target_catalog.infer_device_type({"ssh_user": "pi"}) == "raspberrypi"
    assert target_catalog.infer_device_type({"device_type": "bbb"}) == "bbb"


def test_classify_player_version_stable():
    info = target_catalog.classify_player_version("8.2")
    assert info["player_line"] == "8.x"
    assert info["player_group"] == "8.x"
    assert info["player_channel"] == "stable"
    assert info["player_major"] == 8


def test_classify_player_version_beta():
    info = target_catalog.classify_player_version("8.2-beta")
    assert info["player_line"] == "8.x"
    assert info["player_channel"] == "beta"
    assert "beta" in info["player_group"]


def test_group_by_device_type():
    records = [
        {"name": "a", "device_type": "orangepi"},
        {"name": "b", "device_type": "orangepi"},
        {"name": "c", "device_type": "raspberrypi"},
    ]
    grouped = target_catalog.group_by_device_type(records)
    assert grouped["total"] == 3
    assert len(grouped["groups"]) == 2
    orangepi = next(g for g in grouped["groups"] if g["device_type"] == "orangepi")
    assert orangepi["count"] == 2


def test_group_by_player_version():
    records = [
        {"name": "a", "player_group": "8.x", "player_version": "8.2"},
        {"name": "b", "player_group": "8.x", "player_version": "8.1"},
        {"name": "c", "player_group": "7.x", "player_version": "7.5"},
    ]
    grouped = target_catalog.group_by_player_version(records)
    assert grouped["total"] == 3
    eight = next(g for g in grouped["groups"] if g["player_group"] == "8.x")
    assert eight["count"] == 2
    assert set(eight["versions"]) == {"8.1", "8.2"}
