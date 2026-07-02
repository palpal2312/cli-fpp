"""Nhận ảnh (file/URL), phân tích và đề xuất xoay trước upload."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from PIL import Image, ImageOps

from cli_fpp.core import image_tools
from cli_fpp.core import media_orientation
from cli_fpp.core.media_orientation import RotateArg, resolve_rotate

IMAGE_EXTS = image_tools.IMAGE_EXTS
_URL_RE = re.compile(r"^https?://", re.I)


def is_url(src: str) -> bool:
    return bool(_URL_RE.match(src.strip()))


def _filename_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name or "download.jpg"
    if Path(name).suffix.lower() not in IMAGE_EXTS:
        name = f"{Path(name).stem or 'download'}.jpg"
    return name


def fetch_source(src: str, *, dest_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """Tải URL hoặc trả path file local. Returns (path, meta)."""
    src = src.strip()
    if is_url(src):
        dest = (dest_dir or Path(tempfile.mkdtemp(prefix="cli-fpp-fetch-"))) / _filename_from_url(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(src, timeout=60, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return dest, {"input": src, "source_type": "url", "local_path": str(dest)}
    path = Path(src).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {src}")
    return path, {"input": src, "source_type": "file", "local_path": str(path)}


def probe_image(path: Path) -> dict[str, Any]:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
    aspect = "portrait" if h > w else ("landscape" if w > h else "square")
    return {"width": w, "height": h, "aspect": aspect, "size_label": f"{w}x{h}"}


def _device_summary(profile: dict[str, Any]) -> dict[str, Any]:
    portrait = profile.get("device_portrait", False)
    geom = profile.get("fb_geometry") or {}
    monitor = profile.get("monitor") or {}
    return {
        "host": profile.get("host"),
        "hdmi_status": profile.get("hdmi_status"),
        "display_mode": "portrait" if portrait else "landscape",
        "orientation": profile.get("orientation"),
        "fb_rotate": profile.get("fb_rotate"),
        "boot_rotate_degrees": profile.get("boot_rotate_degrees"),
        "canvas": {
            "width": profile.get("canvas_width"),
            "height": profile.get("canvas_height"),
            "label": f"{profile.get('canvas_width')}x{profile.get('canvas_height')}",
        },
        "monitor": {
            "name": monitor.get("name") or monitor.get("model") or "unknown",
            "edid": monitor.get("serial") or monitor.get("manufacturer"),
        },
    }


def _expand_sources(sources: list[str]) -> list[str]:
    """Mở rộng thư mục thành danh sách file ảnh."""
    out: list[str] = []
    for raw in sources:
        raw = raw.strip()
        if is_url(raw):
            out.append(raw)
            continue
        p = Path(raw)
        if p.is_dir():
            out.extend(
                str(f) for f in sorted(p.rglob("*")) if f.is_file() and f.suffix.lower() in IMAGE_EXTS
            )
        else:
            out.append(raw)
    return out


def propose_media(
    sources: list[str],
    *,
    display_profile: dict[str, Any] | None = None,
    rotate: RotateArg = "auto",
) -> dict[str, Any]:
    """Kiểm tra thiết bị + từng ảnh → đề xuất xoay trước upload (không upload)."""
    profile = display_profile or media_orientation.get_display_profile()
    device = _device_summary(profile)
    canvas_w = int(profile.get("canvas_width") or 1920)
    canvas_h = int(profile.get("canvas_height") or 1080)

    expanded = _expand_sources(sources)
    if not expanded:
        return {
            "device": device,
            "display_profile": profile,
            "items": [],
            "summary": "Không tìm thấy ảnh (jpg/png) trong nguồn",
            "recommendation": {"transpose_before_upload": False},
            "recommended_cli": [],
            "agent_next_steps": ["Kiểm tra path/URL hoặc định dạng file"],
        }

    tmp = Path(tempfile.mkdtemp(prefix="cli-fpp-propose-"))
    items: list[dict[str, Any]] = []
    try:
        for raw in expanded:
            try:
                path, meta = fetch_source(raw, dest_dir=tmp)
                if path.suffix.lower() not in IMAGE_EXTS:
                    items.append(
                        {
                            **meta,
                            "error": f"Chỉ hỗ trợ ảnh propose: {', '.join(sorted(IMAGE_EXTS))}",
                        }
                    )
                    continue
                probe = probe_image(path)
                deg, reason = resolve_rotate(
                    probe["width"], probe["height"], profile, rotate=rotate
                )
                items.append(
                    {
                        **meta,
                        **probe,
                        "proposed_rotate_degrees": deg,
                        "proposed_reason": reason,
                        "proposed_output_size": f"{canvas_w}x{canvas_h}",
                        "will_transpose": deg != 0,
                        "ready_to_upload": True,
                    }
                )
            except Exception as exc:
                items.append({"input": raw, "error": str(exc), "ready_to_upload": False})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    needs_rotate = [i for i in items if i.get("will_transpose")]
    summary_parts = [
        f"Thiết bị {device['host']}: màn {device['display_mode']} ({device['orientation']}), "
        f"canvas {device['canvas']['label']}",
    ]
    if needs_rotate:
        summary_parts.append(
            f"{len(needs_rotate)}/{len(items)} ảnh dọc → đề xuất xoay trước upload"
        )
    else:
        summary_parts.append("Không cần xoay ảnh trước upload")

    local_paths = [i["local_path"] for i in items if i.get("local_path") and not i.get("error")]
    recommended_cli: list[str] = ["cli-fpp --json media propose <path-hoặc-url>"]
    upload_targets = [i["input"] for i in items if i.get("ready_to_upload") and not i.get("error")]
    if upload_targets:
        if len(upload_targets) == 1:
            recommended_cli.append(f'cli-fpp --json --yes media upload "{upload_targets[0]}"')
        else:
            recommended_cli.append(
                "cli-fpp --json --yes media upload <từng-file-hoặc-thư-mục>"
            )

    return {
        "device": device,
        "display_profile": profile,
        "items": items,
        "summary": "; ".join(summary_parts),
        "recommendation": {
            "transpose_before_upload": bool(needs_rotate),
            "default_rotate": rotate,
            "proposed_upload_command": recommended_cli[-1] if len(recommended_cli) > 1 else None,
        },
        "recommended_cli": recommended_cli,
        "agent_next_steps": [
            "1. Trình bày device + proposed_rotate cho user",
            "2. User đồng ý → chạy recommended_cli upload",
            "3. (Tuỳ chọn) playlist play để hiển thị",
        ],
    }
