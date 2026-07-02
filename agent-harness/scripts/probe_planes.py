#!/usr/bin/env python3
import paramiko
from pathlib import Path

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.1.39", username="orangepi", password="orangepi", timeout=20)
_, o, _ = c.exec_command("modetest -M rockchip -p 2>/dev/null", timeout=60)
text = o.read().decode()
out = Path(__file__).with_name("modetest_planes.txt")
out.write_text(text, encoding="utf-8")
print("wrote", out, len(text), "chars")
for i, line in enumerate(text.splitlines()):
    if "rotation:" in line or (i > 0 and "rotation:" in text.splitlines()[i-1]):
        print(text.splitlines()[max(0,i-8):i+3])
c.close()
