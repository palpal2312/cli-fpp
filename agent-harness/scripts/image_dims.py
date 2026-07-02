#!/usr/bin/env python3
import json
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
print(host_ssh.run_ssh(
    "docker exec fpp-docker sh -c 'for f in /home/fpp/media/images/*.jpg; do file \"$f\"; done'",
    conf=conf,
))
