#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "docker exec fpp-docker ls /opt/fpp/src/playlist/ | grep -i video",
    "docker exec fpp-docker grep -rn pipewire /opt/fpp/src/ 2>/dev/null | head -15",
    "docker exec fpp-docker which ffmpeg gst-launch-1.0 2>/dev/null",
    "docker exec fpp-docker sh -c 'grep -i gstreamer /home/fpp/media/logs/fppd.log 2>/dev/null | tail -10'",
    "ls /home/orangepi/fpp/Docker/media/videos/ 2>/dev/null | head -5",
]
for c in cmds:
    print("===", c[:70], "===")
    print(host_ssh.run_ssh(c, conf=conf))
