"""Tests for media orientation auto-transpose logic."""

from __future__ import annotations

from cli_fpp.core.media_orientation import (
    get_display_profile,
    is_portrait_display,
    is_portrait_media,
    resolve_rotate,
)


def test_is_portrait_media():
    assert is_portrait_media(1080, 1920) is True
    assert is_portrait_media(1920, 1080) is False


def test_is_portrait_display_fb_rotate():
    assert is_portrait_display({"fb_rotate": 1}) is True
    assert is_portrait_display({"fb_rotate": 0}) is False


def test_is_portrait_display_boot_rotate():
    assert is_portrait_display({"boot_rotate_degrees": 90}) is True


def test_resolve_rotate_auto_portrait():
    profile = {"fb_rotate": 1, "orientation": "portrait-right", "boot_rotate_degrees": 90}
    deg, reason = resolve_rotate(1080, 1920, profile, rotate="auto")
    assert deg == 90
    assert "portrait" in reason


def test_resolve_rotate_auto_landscape_device():
    profile = {"fb_rotate": 0, "orientation": "landscape"}
    deg, _ = resolve_rotate(1080, 1920, profile, rotate="auto")
    assert deg == 0


def test_resolve_rotate_auto_landscape_media():
    profile = {"fb_rotate": 1, "orientation": "portrait-right"}
    deg, _ = resolve_rotate(1920, 1080, profile, rotate="auto")
    assert deg == 0


def test_resolve_rotate_portrait_left():
    profile = {"fb_rotate": 3, "orientation": "portrait-left", "boot_rotate_degrees": 270}
    deg, _ = resolve_rotate(1080, 1920, profile, rotate="auto")
    assert deg == 270


def test_resolve_rotate_manual_override():
    profile = {"fb_rotate": 0}
    deg, reason = resolve_rotate(1080, 1920, profile, rotate=180)
    assert deg == 180
    assert "manual" in reason
