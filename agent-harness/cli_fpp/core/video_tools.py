"""Local video prep for FPP — transpose + scale via ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from cli_fpp.core.image_tools import PrepareResult
from cli_fpp.core.media_orientation import RotateArg, resolve_rotate

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _iter_videos(src: Path) -> Iterable[Path]:
    if src.is_file():
        if src.suffix.lower() in VIDEO_EXTS:
            yield src
        return
    for p in src.rglob("*"):
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS:
            yield p


def _probe_size(path: Path) -> tuple[int, int]:
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe not found — cài ffmpeg (gồm ffprobe)")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    w, h = out.split("x")
    return int(w), int(h)


def _ffmpeg_transpose_filter(degrees: int) -> str:
    # ffmpeg transpose: 1=CW 90°, 2=CCW 90°
    if degrees == 90:
        return "transpose=1"
    if degrees == 270:
        return "transpose=2"
    if degrees == 180:
        return "transpose=1,transpose=1"
    return ""


def prepare_videos(
    src: Path,
    dst: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    rotate: RotateArg = "auto",
    display_profile: dict | None = None,
    overwrite: bool = False,
) -> PrepareResult:
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not found — cài ffmpeg để prepare video")

    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    files = list(_iter_videos(src))
    total = len(files)
    processed = 0
    skipped = 0
    errors: list[dict] = []

    for fp in files:
        rel = fp.relative_to(src if src.is_dir() else fp.parent)
        out_rel = rel.with_suffix(".mp4")
        out_path = dst / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and not overwrite:
            skipped += 1
            continue

        try:
            sw, sh = _probe_size(fp)
            deg = 0
            reason = ""
            if display_profile is not None:
                deg, reason = resolve_rotate(sw, sh, display_profile, rotate=rotate)
            elif rotate != "auto":
                deg = int(rotate)

            vf_parts: list[str] = []
            if deg:
                vf_parts.append(_ffmpeg_transpose_filter(deg))
            vf_parts.append(
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}"
            )
            vf = ",".join(vf_parts)

            cmd = [
                "ffmpeg",
                "-y" if overwrite else "-n",
                "-i",
                str(fp),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(out_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            processed += 1
        except subprocess.CalledProcessError as exc:
            errors.append({"file": str(fp), "error": (exc.stderr or str(exc))[:500]})
        except Exception as exc:
            errors.append({"file": str(fp), "error": str(exc)})

    return PrepareResult(total=total, processed=processed, skipped=skipped, errors=errors)
