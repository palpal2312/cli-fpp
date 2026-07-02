#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
out = host_ssh.run_ssh(
    "docker stop fpp-docker 2>&1; "
    "docker ps -a --filter name=fpp-docker --format '{{.Names}} {{.Status}}'",
    conf=conf,
)
print(out)
