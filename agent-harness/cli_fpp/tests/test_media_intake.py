"""Tests for media intake / propose flow."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from cli_fpp.core import media_intake


def test_is_url():
    assert media_intake.is_url("https://x.com/a.jpg") is True
    assert media_intake.is_url("/tmp/a.jpg") is False


def test_probe_image_portrait(tmp_path: Path):
    p = tmp_path / "p.jpg"
    Image.new("RGB", (1080, 1920), "red").save(p)
    probe = media_intake.probe_image(p)
    assert probe["aspect"] == "portrait"
    assert probe["size_label"] == "1080x1920"


def test_propose_portrait_device(tmp_path: Path):
    p = tmp_path / "ad.jpg"
    Image.new("RGB", (1080, 1920), "blue").save(p)
    profile = {
        "host": "192.168.1.39",
        "device_portrait": True,
        "display_mode": "portrait",
        "orientation": "portrait-right",
        "fb_rotate": 1,
        "boot_rotate_degrees": 90,
        "canvas_width": 1920,
        "canvas_height": 1080,
        "fb_geometry": {"width": 1920, "height": 1080},
        "hdmi_status": "connected",
        "monitor": {"name": "XMI"},
    }

    result = media_intake.propose_media([str(p)], display_profile=profile)
    assert result["device"]["display_mode"] == "portrait"
    assert result["device"]["canvas"]["label"] == "1920x1080"
    assert result["items"][0]["proposed_rotate_degrees"] == 90
    assert result["recommendation"]["transpose_before_upload"] is True
    assert "media upload" in result["recommended_cli"][-1]


def test_propose_landscape_no_rotate(tmp_path: Path):
    p = tmp_path / "wide.jpg"
    Image.new("RGB", (1920, 1080), "green").save(p)
    profile = {
        "host": "192.168.1.39",
        "device_portrait": False,
        "display_mode": "landscape",
        "orientation": "landscape",
        "fb_rotate": 0,
        "boot_rotate_degrees": 0,
        "canvas_width": 1920,
        "canvas_height": 1080,
        "fb_geometry": {"width": 1920, "height": 1080},
        "hdmi_status": "connected",
        "monitor": {},
    }
    result = media_intake.propose_media([str(p)], display_profile=profile)
    assert result["items"][0]["proposed_rotate_degrees"] == 0
    assert result["recommendation"]["transpose_before_upload"] is False


def test_propose_directory(tmp_path: Path):
    d = tmp_path / "batch"
    d.mkdir()
    Image.new("RGB", (1080, 1920), "red").save(d / "a.jpg")
    Image.new("RGB", (1920, 1080), "blue").save(d / "b.jpg")
    profile = {
        "host": "192.168.1.39",
        "device_portrait": True,
        "display_mode": "portrait",
        "orientation": "portrait-right",
        "fb_rotate": 1,
        "boot_rotate_degrees": 90,
        "canvas_width": 1920,
        "canvas_height": 1080,
        "fb_geometry": {"width": 1920, "height": 1080},
        "hdmi_status": "connected",
        "monitor": {},
    }
    result = media_intake.propose_media([str(d)], display_profile=profile)
    assert len(result["items"]) == 2
    by_name = {Path(i["input"]).name: i for i in result["items"]}
    assert by_name["a.jpg"]["proposed_rotate_degrees"] == 90
    assert by_name["b.jpg"]["proposed_rotate_degrees"] == 0
