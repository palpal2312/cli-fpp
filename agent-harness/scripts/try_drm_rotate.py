#!/usr/bin/env python3
"""Try DRM plane rotation on Rockchip RK356x."""
import paramiko
import sys

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.1.39", username="orangepi", password="orangepi", timeout=20)

def run(cmd, sudo=False):
    if sudo:
        cmd = "echo orangepi | sudo -S bash -c " + repr(cmd)
    print(">>>", cmd[:120])
    _, o, e = c.exec_command(cmd, timeout=90)
    out = (o.read() + e.read()).decode()
    print(out[:4000] or "(empty)")
    return out

# Active plane from debugfs
run("grep -A12 'plane\\[57\\]' /sys/kernel/debug/dri/0/state 2>/dev/null | head -15", sudo=True)
run("modetest -M rockchip -p 2>/dev/null | sed -n '/57 Smart0/,/^$/p' | head -40")

# DRM rotation: rotate-90 = 0x2 (not sysfs fb_rotate=1)
# connector 114, crtc 85, plane 57
run(
    "modetest -M rockchip -w 57:rotation:2 2>&1; "
    "sleep 1; "
    "modetest -M rockchip -p 2>/dev/null | sed -n '/57 Smart0/,/rotation/p' | tail -5",
    sudo=True,
)

# Also try connector/crtc level if plane write fails
run("modetest -M rockchip -w 57:73:2 2>&1", sudo=True)

run("cat /sys/class/graphics/fb0/rotate", sudo=True)
c.close()
