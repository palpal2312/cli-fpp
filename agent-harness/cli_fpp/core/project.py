"""Configuration and connection management for cli-fpp."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".cli-fpp"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS: dict[str, Any] = {
    "base_url": "http://fpp.local",
}


def load_config() -> dict[str, Any]:
    """Load config from file, overlaid with environment variables."""
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    if url := os.environ.get("FPP_BASE_URL"):
        cfg["base_url"] = url
    return cfg


def save_config(cfg: dict[str, Any]) -> Path:
    """Persist config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(CONFIG_DIR), 0o700)
    except OSError:
        pass
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(str(CONFIG_FILE), 0o600)
    except OSError:
        pass
    return CONFIG_FILE


def get_connection(base_url: str | None = None) -> str:
    """Resolve FPP base URL from args, env, or config file."""
    cfg = load_config()
    url = (base_url or cfg.get("base_url") or "").strip()
    if not url:
        raise ValueError(
            "FPP base URL not configured. Use --url, FPP_BASE_URL, or: config set base_url <url>"
        )
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url.rstrip("/")
