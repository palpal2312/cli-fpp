#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "hostname; whoami; uptime",
    "grep extraargs /boot/orangepiEnv.txt",
    "cat /sys/class/graphics/fb0/rotate",
    "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null",
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:81/ 2>/dev/null || echo FPP_down",
]
for c in cmds:
    print(">>>", c)
    print(host_ssh.run_ssh(c, conf=conf))
    print()
