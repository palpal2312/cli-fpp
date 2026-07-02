#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "cat /proc/cmdline",
    "dmesg 2>/dev/null | grep -iE 'rotate|video=' | tail -10",
    "cat /sys/class/graphics/fb0/rotate",
    "fbset -s -fb /dev/fb0 2>/dev/null | head -3",
]
for cmd in cmds:
    print("===", cmd)
    print(host_ssh.run_ssh(cmd, conf=conf, sudo=cmd.startswith("dmesg")))
