#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "grep extraargs /boot/orangepiEnv.txt",
    "cat /proc/cmdline | tr ' ' '\\n' | grep -E 'video|rotate'",
    "cat /sys/class/graphics/fb0/rotate",
    "echo orangepi | sudo -S cat /sys/kernel/debug/dri/0/state 2>/dev/null | grep -E 'rotation=|crtc-pos|size=' | head -8",
    "docker exec fpp-docker cat /home/fpp/media/config/co-other.json",
]
for cmd in cmds:
    print("===", cmd[:80])
    print(host_ssh.run_ssh(cmd, conf=conf, sudo=cmd.startswith("echo orangepi"))[:2000])
    print()
