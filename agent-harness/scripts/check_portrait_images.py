#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "grep extraargs /boot/orangepiEnv.txt",
    "cat /proc/cmdline | tr ' ' '\\n' | grep video",
    "docker ps --filter name=fpp-docker --format '{{.Status}}'",
    "docker exec fpp-docker cat /home/fpp/media/config/co-other.json 2>/dev/null",
    "docker exec fpp-docker ls /home/fpp/media/images/ 2>/dev/null | head -10",
    "docker exec fpp-docker sh -c 'grep FBMatrix /home/fpp/media/logs/fppd.log 2>/dev/null | tail -8'",
    "docker exec fpp-docker sh -c 'grep IOCTLFrameBuffer /home/fpp/media/logs/fppd.log 2>/dev/null | tail -8'",
]
for cmd in cmds:
    print("===", cmd)
    print(host_ssh.run_ssh(cmd, conf=conf)[:2000])
    print()
