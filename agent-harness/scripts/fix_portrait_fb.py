#!/usr/bin/env python3
"""Set FPP VirtualMatrix to portrait 1080x1920 and restart fppd."""
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
            "width": 1080,
            "height": 1920,
        }
    ]
}
body = json.dumps(co, indent="\t") + "\n"
b64 = base64.b64encode(body.encode()).decode()
path = "/home/orangepi/fpp/Docker/media/config/co-other.json"

cmds = [
    f"echo {b64} | base64 -d | tee {path} > /dev/null",
    f"docker cp {path} fpp-docker:/home/fpp/media/config/co-other.json",
    "docker restart fpp-docker",
]
for c in cmds:
    print(">>>", c[:70])
    print(host_ssh.run_ssh(c, conf=conf, sudo=c.startswith("docker restart"))[:500])
    print()

print("waiting for fpp...")
import time
time.sleep(25)
print(host_ssh.run_ssh(
    "docker exec fpp-docker cat /home/fpp/media/config/co-other.json",
    conf=conf,
))
