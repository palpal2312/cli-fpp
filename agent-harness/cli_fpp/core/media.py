"""Media and sequence file listing — mirrors playlist dropdown / file manager."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from cli_fpp.core import image_tools
from cli_fpp.core import media_intake
from cli_fpp.core import media_orientation
from cli_fpp.core import video_tools
from cli_fpp.core.media_orientation import RotateArg
from cli_fpp.utils import fpp_backend as api

IMAGE_EXTS = image_tools.IMAGE_EXTS
VIDEO_EXTS = video_tools.VIDEO_EXTS


def list_media(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/media", base_url=base_url)


def list_sequences(*, base_url: str | None = None) -> Any:
    return api.api_get("/api/sequence", base_url=base_url)


def media_duration(file: str, *, base_url: str | None = None) -> Any:
    return api.api_get(f"/api/media/{quote(file, safe='')}/duration", base_url=base_url)


def sequence_meta(file: str, *, base_url: str | None = None) -> Any:
    return api.api_get(f"/api/sequence/{quote(file, safe='')}/meta", base_url=base_url)


def _media_dir_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "images"
    if ext in VIDEO_EXTS:
        return "videos"
    raise ValueError(f"Unsupported media type {ext!r} — dùng jpg/png hoặc mp4/mov/mkv")


def upload_file(
    local_path: Path,
    dirname: str,
    *,
    remote_name: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Upload one file to FPP via POST /api/file/{DirName}/{Name} (raw body)."""
    local_path = Path(local_path)
    name = remote_name or local_path.name
    base = (base_url or api._get_base_url()).rstrip("/")
    url = f"{base}/api/file/{quote(dirname, safe='')}/{quote(name, safe='')}"
    resp = requests.post(
        url,
        data=local_path.read_bytes(),
        auth=api._get_auth(),
        headers={"Content-Type": "application/octet-stream"},
        timeout=api.DEFAULT_TIMEOUT,
        verify=api._verify_ssl(),
    )
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text, "file": name, "dir": dirname}


def upload_prepared(
    src: Path | str,
    *,
    dirname: str | None = None,
    auto_orient: bool = True,
    rotate: RotateArg = "auto",
    width: int = 1920,
    height: int = 1080,
    overwrite: bool = False,
    base_url: str | None = None,
    display_profile: dict | None = None,
) -> dict[str, Any]:
    """Prepare (auto transpose if portrait display) then upload to FPP."""
    if isinstance(src, str) and media_intake.is_url(src):
        tmp_fetch = Path(tempfile.mkdtemp(prefix="cli-fpp-upload-fetch-"))
        try:
            path, _ = media_intake.fetch_source(src, dest_dir=tmp_fetch)
            return _upload_prepared_path(
                path,
                dirname=dirname,
                auto_orient=auto_orient,
                rotate=rotate,
                width=width,
                height=height,
                overwrite=overwrite,
                base_url=base_url,
                display_profile=display_profile,
            )
        finally:
            shutil.rmtree(tmp_fetch, ignore_errors=True)

    return _upload_prepared_path(
        Path(src),
        dirname=dirname,
        auto_orient=auto_orient,
        rotate=rotate,
        width=width,
        height=height,
        overwrite=overwrite,
        base_url=base_url,
        display_profile=display_profile,
    )


def _upload_prepared_path(
    src: Path,
    *,
    dirname: str | None = None,
    auto_orient: bool = True,
    rotate: RotateArg = "auto",
    width: int = 1920,
    height: int = 1080,
    overwrite: bool = False,
    base_url: str | None = None,
    display_profile: dict | None = None,
) -> dict[str, Any]:
    """Internal: upload from local path."""
    profile = display_profile
    if auto_orient and profile is None:
        profile = media_orientation.get_display_profile()

    canvas_w = int((profile or {}).get("canvas_width") or width)
    canvas_h = int((profile or {}).get("canvas_height") or height)
    rot: RotateArg | int = rotate if auto_orient else (int(rotate) if rotate != "auto" else 0)
    prof = profile if auto_orient else None

    tmp = Path(tempfile.mkdtemp(prefix="cli-fpp-upload-"))
    result: dict[str, Any] = {
        "display_profile": profile,
        "auto_orient": auto_orient,
        "uploads": [],
    }

    try:
        has_images = src.suffix.lower() in IMAGE_EXTS if src.is_file() else any(
            p.suffix.lower() in IMAGE_EXTS for p in src.rglob("*") if p.is_file()
        )
        has_videos = src.suffix.lower() in VIDEO_EXTS if src.is_file() else any(
            p.suffix.lower() in VIDEO_EXTS for p in src.rglob("*") if p.is_file()
        )

        if has_images:
            img_out = tmp / "images"
            img_prep = image_tools.prepare_images(
                src,
                img_out,
                width=canvas_w,
                height=canvas_h,
                rotate=rot,
                display_profile=prof,
                overwrite=True,
            )
            result["images"] = img_prep.to_dict()
            for detail in img_prep.details:
                out = Path(detail["output"])
                target = dirname or "images"
                result["uploads"].append(
                    {
                        "local": str(out),
                        "rotate_applied": detail.get("rotate_applied"),
                        "reason": detail.get("reason"),
                        "fpp": upload_file(
                            out,
                            target,
                            remote_name=out.name,
                            base_url=base_url,
                        ),
                    }
                )

        if has_videos:
            if not video_tools.ffmpeg_available():
                result["video_warning"] = (
                    "ffmpeg không có — bỏ qua video. Cài ffmpeg hoặc dùng media prepare-videos trước."
                )
            else:
                vid_out = tmp / "videos"
                vid_prep = video_tools.prepare_videos(
                    src,
                    vid_out,
                    width=canvas_w,
                    height=canvas_h,
                    rotate=rot,
                    display_profile=prof,
                    overwrite=True,
                )
                result["videos"] = vid_prep.to_dict()
                for out in vid_out.rglob("*.mp4"):
                    target = dirname or "videos"
                    result["uploads"].append(
                        {
                            "local": str(out),
                            "fpp": upload_file(
                                out,
                                target,
                                remote_name=out.name,
                                base_url=base_url,
                            ),
                        }
                    )

        result["uploaded"] = len(result["uploads"])
        return result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
