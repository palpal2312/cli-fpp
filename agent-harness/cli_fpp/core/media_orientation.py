"""Detect host display orientation and decide media transpose before FPP upload."""

from __future__ import annotations

import re
from typing import Any, Literal

from cli_fpp.core import host_ssh

RotateDeg = Literal[0, 90, 180, 270]
RotateArg = RotateDeg | Literal["auto"]

PORTRAIT_FB_ROTATE = {1, 3}
PORTRAIT_ORIENTATIONS = {"portrait-right", "portrait-left", "portrait"}


def is_portrait_display(profile: dict[str, Any]) -> bool:
    if profile.get("fb_rotate") in PORTRAIT_FB_ROTATE:
        return True
    orient = str(profile.get("orientation", "")).lower()
    if orient in PORTRAIT_ORIENTATIONS:
        return True
    boot = profile.get("boot_rotate_degrees") or 0
    return boot in (90, 270)


def is_portrait_media(width: int, height: int) -> bool:
    return height > width


def _boot_rotate_degrees(cmdline: str) -> int:
    m = re.search(r"rotate[=:](\d+)", cmdline)
    return int(m.group(1)) if m else 0


def get_display_profile(*, conf: host_ssh.SSHConfig | None = None) -> dict[str, Any]:
    """SSH host display status + derived canvas/transpose hints for media prep."""
    conf = conf or host_ssh.get_ssh_config()
    status = host_ssh.display_status(conf=conf)
    cmdline = host_ssh.run_ssh("cat /proc/cmdline 2>/dev/null", conf=conf)
    boot_rotate = _boot_rotate_degrees(cmdline)
    geom = status.get("fb_geometry") or {}
    canvas_w = int(geom.get("width") or 1920)
    canvas_h = int(geom.get("height") or 1080)
    portrait = is_portrait_display({**status, "boot_rotate_degrees": boot_rotate})

    profile = {
        **status,
        "boot_rotate_degrees": boot_rotate,
        "device_portrait": portrait,
        "display_mode": "portrait" if portrait else "landscape",
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "canvas_label": f"{canvas_w}x{canvas_h}",
        "media_note": (
            "Màn portrait: file dọc (cao > rộng) tự transpose về canvas ngang trước upload. "
            "Ảnh dùng fb0; video cần VLC/GStreamer (Docker Orange Pi thường lỗi pipewire)."
        ),
    }
    return profile


def resolve_rotate(
    source_width: int,
    source_height: int,
    profile: dict[str, Any],
    *,
    rotate: RotateArg = "auto",
) -> tuple[int, str]:
    """Return clockwise degrees to apply (0 = skip) and reason string."""
    if rotate != "auto":
        deg = int(rotate)
        return deg, f"manual rotate={deg}°"

    if not is_portrait_display(profile):
        return 0, "device landscape — giữ nguyên hướng media"

    if not is_portrait_media(source_width, source_height):
        return 0, "media ngang — không cần transpose"

    orient = str(profile.get("orientation", "")).lower()
    fb_rotate = profile.get("fb_rotate", 0)
    if orient == "portrait-left" or fb_rotate == 3 or profile.get("boot_rotate_degrees") == 270:
        return 270, "device portrait-left + media dọc → transpose 270°"

    return 90, "device portrait + media dọc → transpose 90°"
