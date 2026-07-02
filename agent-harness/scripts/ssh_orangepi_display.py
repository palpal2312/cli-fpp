#!/usr/bin/env python3
"""One-shot SSH to Orange Pi — display / EDID probe."""
from __future__ import annotations

import sys

try:
    import paramiko
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

HOST = "192.168.1.39"
USER = "orangepi"
PASSWORD = "orangepi"

COMMANDS = [
    "uname -a",
    "hostname",
    "cat /etc/os-release 2>/dev/null | head -6",
    "ls -la /dev/fb* 2>/dev/null",
    "fbset -s -fb /dev/fb0 2>/dev/null || true",
    r"""for f in /sys/class/drm/*/edid; do [ -s "$f" ] && echo "EDID_FILE=$f" && xxd -l 128 "$f" 2>/dev/null | head -1; done""",
    "command -v edid-decode xrandr 2>/dev/null; which edid-decode xrandr 2>/dev/null",
    "xrandr --query 2>/dev/null",
    r"""for f in /sys/class/drm/*/edid; do
  if [ -s "$f" ]; then
    echo "=== $f ==="
    if command -v edid-decode >/dev/null; then edid-decode "$f" 2>/dev/null | grep -E 'Manufacturer|Model|Monitor|Serial|Product|Display Product'; fi
  fi
done""",
    'docker ps --format "{{.Names}} {{.Image}}" 2>/dev/null | head -10',
    "cat /sys/class/drm/card*/status 2>/dev/null; ls /sys/class/drm/ 2>/dev/null",
]


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD, timeout=20)
    try:
        for cmd in COMMANDS:
            print(f"=== {cmd}")
            _, stdout, stderr = client.exec_command(cmd, timeout=45)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            if out.strip():
                print(out.rstrip())
            if err.strip():
                print(err.rstrip())
            if not out.strip() and not err.strip():
                print("(empty)")
            print()
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
