#!/usr/bin/env python3
"""Research FPP rotation/orientation capabilities on live instance."""
from __future__ import annotations

import json
import os
import sys

from cli_fpp.core import host_ssh
from cli_fpp.utils import fpp_backend as api

BASE = os.environ.get("FPP_BASE_URL", "http://192.168.1.39:81")
AUTH = ("admin", "haruhi")
conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")


def section(title: str) -> None:
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def api_try(path: str) -> None:
    try:
        data = api.api_get(path, base_url=BASE, auth=AUTH)
        print(json.dumps(data, indent=2)[:6000])
    except Exception as e:
        print(f"ERR {path}: {e}")


def ssh_grep(pattern: str, paths: str) -> None:
    cmd = f"docker exec fpp-docker grep -rniE '{pattern}' {paths} 2>/dev/null | head -50"
    print(host_ssh.run_ssh(cmd, conf=conf))


def main() -> int:
    section("FPP API — overlays / outputs")
    for p in [
        "/api/overlays/models",
        "/api/overlays/settings",
        "/api/channel/output/list",
        "/api/settings/outputs",
    ]:
        print(f"\n--- {p} ---")
        api_try(p)

    section("Host config files")
    for f in [
        "cat /home/orangepi/fpp/Docker/media/config/co-other.json",
        "ls -la /home/orangepi/fpp/Docker/media/config/",
        "cat /home/orangepi/fpp/Docker/media/config/overlayModels.json 2>/dev/null || echo NO overlayModels.json",
    ]:
        print(f"\n--- {f} ---")
        print(host_ssh.run_ssh(f, conf=conf))

    section("FPP source — framebuffer / channel output rotation")
    ssh_grep("rotate|flipHorizontal|flipVertical|orientation", "/opt/fpp/src/framebuffer /opt/fpp/src/channeloutput")

    section("FPP source — playlist image rotation")
    ssh_grep("rotate|flip|orientation", "/opt/fpp/src/playlist")

    section("FPP www — UI rotation fields")
    ssh_grep("rotate|flipHorizontal|flipVertical", "/opt/fpp/www")

    section("Playlist entries (image options)")
    try:
        from cli_fpp.core import playlist as pl

        for name in ["Haruhi_Test", "Haruhi_rotate"]:
            try:
                d = pl.get_playlist(name, base_url=BASE, auth=AUTH)
                print(f"\n--- playlist {name} ---")
                print(json.dumps(d, indent=2)[:4000])
            except Exception as e:
                print(f"{name}: {e}")
    except Exception as e:
        print(e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
