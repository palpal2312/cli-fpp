#!/usr/bin/env python3
"""Revert co-other to working 1920x1080 FB config."""
import base64
import json
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
co = {
    "channelOutputs": [
        {
            "enabled": 1,
            "type": "VirtualMatrix",
            "startChannel": 1,
            "channelCount": 6220800,
            "modelName": "",
            "invert": False,
            "flipHorizontal": False,
            "device": "fb0",
            "width": 1920,
            "height": 1080,
        }
    ]
}
body = json.dumps(co, indent="\t") + "\n"
b64 = base64.b64encode(body.encode()).decode()
path = "/home/orangepi/fpp/Docker/media/config/co-other.json"
host_ssh.run_ssh(f"echo {b64} | base64 -d | tee {path} > /dev/null", conf=conf)
host_ssh.run_ssh(f"docker cp {path} fpp-docker:/home/fpp/media/config/co-other.json", conf=conf)
print(host_ssh.run_ssh("docker restart fpp-docker", conf=conf, sudo=True))
