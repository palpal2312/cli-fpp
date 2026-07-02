#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "docker exec fpp-docker tail -100 /home/fpp/media/logs/fppd.log 2>/dev/null",
    "docker exec fpp-docker sh -c 'grep -i gstreamer /home/fpp/media/logs/fppd.log 2>/dev/null | tail -30'",
    "docker exec fpp-docker sh -c 'grep -i pipeline /home/fpp/media/logs/fppd.log 2>/dev/null | tail -20'",
    "docker exec fpp-docker cat /home/fpp/media/config/settings.json 2>/dev/null",
]
for cmd in cmds:
    print("===", cmd[:75])
    print(host_ssh.run_ssh(cmd, conf=conf)[:4000])
    print()
