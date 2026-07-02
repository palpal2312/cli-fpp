#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "systemctl status docker.service --no-pager 2>&1 | head -15",
    "systemctl status docker.socket --no-pager 2>&1 | head -10",
    "ls -la /home/orangepi/fpp/Docker/ 2>/dev/null",
    "cat /home/orangepi/fpp/Docker/docker-compose.yml 2>/dev/null",
    "systemctl status fppd.service --no-pager 2>&1 | head -12",
    "ls /etc/systemd/system/*docker*compose* 2>/dev/null; ls /etc/systemd/system/*fpp-docker* 2>/dev/null",
    "which docker-compose docker 2>/dev/null",
]
for c in cmds:
    print("===", c[:95])
    print(host_ssh.run_ssh(c, conf=conf, sudo=c.startswith("systemctl")))
    print()
