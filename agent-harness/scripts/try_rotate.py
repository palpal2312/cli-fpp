#!/usr/bin/env python3
import paramiko, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.1.39", username="orangepi", password="orangepi", timeout=20)

def run(cmd):
    print("===", cmd)
    _, o, e = c.exec_command(cmd, timeout=30)
    out = (o.read() + e.read()).decode()
    print(out or "(empty)")
    return out

run("cat /sys/class/graphics/fb0/rotate")
run("cat /sys/class/graphics/fb0/virtual_size")
run("fbset -s -fb /dev/fb0")

# try portrait: rotate 1 = 90 degrees (typical on fbcon)
run("echo orangepi | sudo -S bash -c 'echo 1 > /sys/class/graphics/fb0/rotate'")
time.sleep(2)
run("cat /sys/class/graphics/fb0/rotate")
run("cat /sys/class/graphics/fb0/virtual_size")
run("fbset -s -fb /dev/fb0")

# restore landscape
run("echo orangepi | sudo -S bash -c 'echo 0 > /sys/class/graphics/fb0/rotate'")
time.sleep(1)
run("cat /sys/class/graphics/fb0/rotate")
run("fbset -s -fb /dev/fb0")
c.close()
