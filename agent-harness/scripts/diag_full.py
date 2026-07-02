#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")
cmds = [
    "docker exec fpp-docker tail -40 /home/fpp/media/logs/fppd.log",
    "docker exec fpp-docker cat /home/fpp/media/config/co-other.json",
    "docker exec fpp-docker ls -la /dev/fb0 /dev/console /dev/tty0 2>&1",
    "cat /sys/class/graphics/fb0/rotate; cat /sys/class/graphics/fb0/virtual_size",
    "grep extraargs /boot/orangepiEnv.txt",
    "docker exec fpp-docker ps aux | grep fppd",
]
for cmd in cmds:
    print("===", cmd[:76])
    print(host_ssh.run_ssh(cmd, conf=conf)[:3000])
    print()
