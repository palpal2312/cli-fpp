#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.1.39", username="orangepi", password="orangepi", timeout=20)
cmds = [
    "modetest -M rockchip -p 2>/dev/null | grep -i rotation",
    "modetest -M rockchip -p 2>/dev/null | sed -n '/^planes:/,/^$/p' | head -50",
    "docker exec fpp-docker cat /home/fpp/media/config/overlayModels.json 2>/dev/null | head -120",
    "docker exec fpp-docker cat /home/fpp/media/config/model-overlays.json 2>/dev/null | head -80",
    "docker exec fpp-docker ls /home/fpp/media/config/ 2>/dev/null",
    "docker exec fpp-docker fpp -V 2>/dev/null; docker exec fpp-docker ps aux 2>/dev/null | grep fppd",
]
for cmd in cmds:
    print("===", cmd)
    _, o, e = c.exec_command(cmd, timeout=60)
    print((o.read() + e.read()).decode() or "(empty)")
    print()
c.close()
