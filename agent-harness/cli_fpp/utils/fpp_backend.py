"""FPP REST API client — HTTP layer for Falcon Player."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote

import requests

try:
    DEFAULT_TIMEOUT = int(os.environ.get("FPP_TIMEOUT", "30"))
except (TypeError, ValueError):
    DEFAULT_TIMEOUT = 30


def _get_base_url() -> str:
    return os.environ.get("FPP_BASE_URL", "").rstrip("/")


def _url(base_url: str | None, path: str) -> str:
    base = (base_url or _get_base_url()).rstrip("/")
    if not base:
        raise ValueError(
            "FPP base URL not configured. Set FPP_BASE_URL env var or pass --url."
        )
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "Accept": "application/json"}


def _handle_response(resp: requests.Response) -> Any:
    if resp.status_code == 204:
        return {}
    content_type = resp.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return {"raw": resp.text}
    return {"raw": resp.text, "content_type": content_type}


def api_request(
    method: str,
    endpoint: str,
    *,
    base_url: str | None = None,
    params: dict[str, Any] | None = None,
    json_data: Any | None = None,
    timeout: int | None = None,
) -> Any:
    """Execute an HTTP request against a running FPP instance."""
    url = _url(base_url, endpoint)
    resp = requests.request(
        method,
        url,
        headers=_headers(),
        params=params,
        json=json_data,
        timeout=timeout or DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return _handle_response(resp)


def api_get(
    endpoint: str,
    *,
    base_url: str | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    return api_request("GET", endpoint, base_url=base_url, params=params)


def api_post(
    endpoint: str,
    data: Any | None = None,
    *,
    base_url: str | None = None,
) -> Any:
    return api_request("POST", endpoint, base_url=base_url, json_data=data)


def api_put(
    endpoint: str,
    data: Any | None = None,
    *,
    base_url: str | None = None,
) -> Any:
    return api_request("PUT", endpoint, base_url=base_url, json_data=data)


def api_delete(
    endpoint: str,
    *,
    base_url: str | None = None,
) -> Any:
    return api_request("DELETE", endpoint, base_url=base_url)


def command_path(command: str, *args: str) -> str:
    """Build /api/command/{command}/arg1/arg2 path segments."""
    segments = [quote(command, safe="")]
    segments.extend(quote(str(a), safe="") for a in args)
    return "/api/command/" + "/".join(segments)


def ping(base_url: str | None = None) -> dict[str, Any]:
    """Lightweight connectivity check via system status."""
    return api_get("/api/system/status", base_url=base_url)
