#!/usr/bin/env python3
"""Fix FPP display: disable host fbcon on fb0, restart FPP."""
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")

fix_cmds = [
    # Tắt framebuffer console trên host — tránh chữ boot/kernel che FPP
    "for v in /sys/class/vtconsole/vtcon*/bind; do echo 0 > $v 2>/dev/null; done",
    "setterm -blank force -term linux </dev/tty1 2>/dev/null || true",
    "setterm -blank force -term linux </dev/tty0 2>/dev/null || true",
    # Restart FPP để grab fb0 lại
    "docker restart fpp-docker",
]

print("=== Fix fbcon + restart FPP ===")
print(host_ssh.run_ssh(" && ".join(fix_cmds), conf=conf, sudo=True))

print("\n=== vtconsole state ===")
print(host_ssh.run_ssh("cat /sys/class/vtconsole/vtcon*/name /sys/class/vtconsole/vtcon*/bind 2>/dev/null", conf=conf))

print("\n=== docker fb0 ===")
print(host_ssh.run_ssh("docker exec fpp-docker ls -la /dev/fb0 2>&1", conf=conf))
