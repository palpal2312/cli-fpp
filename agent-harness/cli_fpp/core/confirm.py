"""Confirmation and dry-run helpers for mutating operations."""

from __future__ import annotations

import sys
from typing import Any

import click


def should_skip_confirm(ctx_obj: dict[str, Any]) -> bool:
    return bool(ctx_obj.get("assume_yes"))


def is_dry_run(ctx_obj: dict[str, Any]) -> bool:
    return bool(ctx_obj.get("dry_run"))


def dry_run_result(action: str, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": True,
        "action": action,
        "would_execute": detail,
        "message": "Không gọi API — dùng bỏ --dry-run để thực thi.",
    }


def require_confirm(
    ctx_obj: dict[str, Any],
    message: str,
    *,
    as_json: bool = False,
) -> bool:
    """Return True if execution should proceed. False = cancelled."""
    if is_dry_run(ctx_obj):
        return True
    if should_skip_confirm(ctx_obj):
        return True
    if not sys.stdin.isatty():
        raise click.ClickException(
            f"Cần xác nhận: {message}. Thêm --yes (đã confirm) hoặc --dry-run."
        )
    return click.confirm(message, default=False)
