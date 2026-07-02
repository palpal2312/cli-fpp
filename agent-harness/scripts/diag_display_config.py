#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "docker ps --filter name=fpp-docker --format '{{.Status}}'",
    "grep extraargs /boot/orangepiEnv.txt",
    "cat /sys/class/graphics/fb0/rotate",
    "docker exec fpp-docker cat /home/fpp/media/config/co-other.json 2>/dev/null",
    "docker exec fpp-docker find /home/fpp/media -name 'overlayModels.json' 2>/dev/null",
    "docker exec fpp-docker cat /home/fpp/media/config/overlayModels.json 2>/dev/null | head -80",
    "docker exec fpp-docker ls /home/fpp/media/config/ 2>/dev/null",
    "docker exec fpp-docker sh -c 'grep PixelOverlayModelFB /home/fpp/media/logs/fppd.log 2>/dev/null | tail -3'",
    "docker exec fpp-docker sh -c 'grep Error /home/fpp/media/logs/fppd.log 2>/dev/null | tail -5'",
]
for cmd in cmds:
    print("===", cmd[:78])
    print(host_ssh.run_ssh(cmd, conf=conf)[:2500])
    print()
