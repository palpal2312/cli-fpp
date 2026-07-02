#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "cat /home/orangepi/fpp/Docker/media/config/co-other.json",
    "docker exec fpp-docker sed -n '130,260p' /opt/fpp/src/channeloutput/FBMatrix.cpp",
    "docker exec fpp-docker grep -n flipHorizontal /opt/fpp/www/co-other-modules.php | head -10",
    "docker exec fpp-docker grep -n invert /opt/fpp/www/co-other-modules.php | head -10",
]
for c in cmds:
    print("===", c[:70], "===")
    print(host_ssh.run_ssh(c, conf=conf))
    print()
