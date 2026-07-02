#!/usr/bin/env python3
"""Extended display probe on Orange Pi."""
from __future__ import annotations

import paramiko

HOST, USER, PASSWORD = "192.168.1.39", "orangepi", "orangepi"
COMMANDS = [
    "echo DISPLAY=$DISPLAY WAYLAND=$WAYLAND_DISPLAY XDG_SESSION_TYPE=$XDG_SESSION_TYPE",
    "ls -la /sys/class/drm/card0-HDMI-A-1/",
    "cat /sys/class/drm/card0-HDMI-A-1/status /sys/class/drm/card0-HDMI-A-1/enabled 2>/dev/null",
    "cat /sys/class/drm/card0-HDMI-A-1/modes 2>/dev/null | head -5",
    "wc -c /sys/class/drm/card0-HDMI-A-1/edid 2>/dev/null; ls -la /sys/class/drm/card0-HDMI-A-1/edid",
    "dmesg 2>/dev/null | grep -iE 'hdmi|edid|display|monitor|xiaomi|drm' | tail -25",
    "sudo cat /sys/class/drm/card0-HDMI-A-1/edid 2>/dev/null | wc -c",
    "DISPLAY=:0 xrandr --query 2>/dev/null || DISPLAY=:0.0 xrandr --query 2>/dev/null",
    "command -v modetest && sudo modetest -c 2>/dev/null | head -40",
    "ps aux | grep -E 'Xorg|wayland|weston|fppd|chrome|kiosk' | grep -v grep | head -15",
    "cat /home/orangepi/.xsession-errors 2>/dev/null | tail -5",
    "ls /tmp/.X11-unix/ 2>/dev/null",
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=20)
for cmd in COMMANDS:
    print(f"=== {cmd}")
    _, stdout, stderr = client.exec_command(cmd, timeout=45, get_pty=True)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    print((out or err or "(empty)").rstrip())
    print()
client.close()
