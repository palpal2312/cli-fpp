"""Local image prep helpers for FPP playlists.

Use this to rotate/resize portrait JPGs trước khi upload lên FPP,
theo đúng canvas của model `FB - fb0` (VirtualMatrix).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps

from cli_fpp.core.media_orientation import RotateArg, resolve_rotate

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}


@dataclass
class PrepareResult:
    total: int
    processed: int
    skipped: int
    errors: list[dict]
    details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "processed": self.processed,
            "skipped": self.skipped,
            "errors": self.errors,
            "details": self.details,
        }


def _iter_input_files(src: Path) -> Iterable[Path]:
    if src.is_file():
        if src.suffix.lower() in IMAGE_EXTS:
            yield src
        return

    for p in src.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def _apply_rotate(im: Image.Image, degrees: int) -> Image.Image:
    if degrees == 90:
        return im.transpose(Image.Transpose.ROTATE_270)
    if degrees == 180:
        return im.transpose(Image.Transpose.ROTATE_180)
    if degrees == 270:
        return im.transpose(Image.Transpose.ROTATE_90)
    return im


def prepare_images(
    src: Path,
    dst: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    rotate: RotateArg = "auto",
    display_profile: dict | None = None,
    overwrite: bool = False,
) -> PrepareResult:
    """Rotate + resize images for FPP framebuffer playlists."""
    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    files = list(_iter_input_files(src))
    total = len(files)
    processed = 0
    skipped = 0
    errors: list[dict] = []
    details: list[dict] = []

    for fp in files:
        rel = fp.relative_to(src if src.is_dir() else fp.parent)
        out_rel = rel.with_suffix(".jpg")
        out_path = dst / out_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and not overwrite:
            skipped += 1
            continue

        try:
            with Image.open(fp) as im:
                im = ImageOps.exif_transpose(im.convert("RGB"))
                sw, sh = im.size
                deg = 0
                reason = ""
                if display_profile is not None:
                    deg, reason = resolve_rotate(sw, sh, display_profile, rotate=rotate)
                elif rotate != "auto":
                    deg = int(rotate)
                    reason = f"manual rotate={deg}°"

                if deg:
                    im = _apply_rotate(im, deg)

                im_out = ImageOps.fit(im, (width, height), method=Image.Resampling.LANCZOS)
                im_out.save(out_path, format="JPEG", quality=90, optimize=True)

            processed += 1
            details.append(
                {
                    "file": str(fp),
                    "output": str(out_path),
                    "source_size": [sw, sh],
                    "rotate_applied": deg,
                    "reason": reason or "no transpose",
                }
            )
        except Exception as exc:
            errors.append({"file": str(fp), "error": str(exc)})

    return PrepareResult(
        total=total,
        processed=processed,
        skipped=skipped,
        errors=errors,
        details=details,
    )
