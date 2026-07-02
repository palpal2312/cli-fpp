#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.1.39", username="orangepi", password="orangepi", timeout=20)
cmds = [
    "which modetest xrandr 2>/dev/null",
    "ls -la /sys/class/graphics/fb0/ 2>/dev/null",
    "modetest -M rockchip -c 2>/dev/null | head -60",
    "modetest -M rockchip -p 2>/dev/null | head -80",
    "for p in /sys/class/drm/card*/card*/rotation; do echo $p; cat $p 2>/dev/null; done",
    "ls /sys/class/drm/card0-HDMI-A-1/",
    "cat /boot/armbianEnv.txt 2>/dev/null; cat /boot/orangepiEnv.txt 2>/dev/null",
]
for cmd in cmds:
    print("===", cmd)
    _, o, e = c.exec_command(cmd, timeout=40)
    print((o.read() + e.read()).decode() or "(empty)")
    print()
c.close()
