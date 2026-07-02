#!/usr/bin/env python3
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.1.39", username="orangepi", password="orangepi", timeout=20)

def run(cmd):
    print("===", cmd)
    _, o, e = c.exec_command(cmd, timeout=60)
    print((o.read() + e.read()).decode() or "(empty)")
    print()

run("docker ps -a --filter name=fpp --format '{{.Names}} {{.Status}} {{.Image}}'")
run("systemctl is-active fppd 2>/dev/null; systemctl status fppd --no-pager 2>/dev/null | head -8")
run("curl -s -o /dev/null -w '%{http_code}' -u admin:haruhi http://127.0.0.1:81/api/fppd/status 2>/dev/null || echo fail")
c.close()
