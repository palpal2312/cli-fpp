#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "docker inspect fpp-docker --format '{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null",
    "docker inspect fpp-docker --format '{{json .Config}}' 2>/dev/null | head -c 2000",
    "systemctl list-unit-files 2>/dev/null | grep -iE 'fpp|docker' | head -20",
    "systemctl is-enabled docker 2>/dev/null",
    "ls -la /etc/systemd/system/*fpp* 2>/dev/null; ls -la /lib/systemd/system/*fpp* 2>/dev/null",
    "docker ps -a --filter name=fpp",
    "cat /etc/docker/daemon.json 2>/dev/null || echo no_daemon_json",
]
for c in cmds:
    print("===", c[:90])
    print(host_ssh.run_ssh(c, conf=conf, sudo=("systemctl" in c and "list" in c)))
    print()
