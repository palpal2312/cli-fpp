#!/usr/bin/env python3
from cli_fpp.core import host_ssh

conf = host_ssh.SSHConfig("192.168.1.39", "orangepi", "orangepi")

sections = [
    ("FBMatrix.h", "docker exec fpp-docker cat /opt/fpp/src/channeloutput/FBMatrix.h"),
    ("PlaylistEntryImage rotate/flip", "docker exec fpp-docker grep -n -iE 'rotate|flip|orient|scale|fit' /opt/fpp/src/playlist/PlaylistEntryImage.cpp | head -40"),
    ("PlaylistEntryImage.h", "docker exec fpp-docker grep -n -iE 'rotate|flip|orient' /opt/fpp/src/playlist/PlaylistEntryImage.h | head -30"),
    ("PixelOverlay FB model", "docker exec fpp-docker grep -n -iE 'rotate|flip|orient' /opt/fpp/src/overlays/PixelOverlayModelFB.cpp | head -40"),
    ("pixeloverlaymodels.php orientation", "docker exec fpp-docker grep -n Orientation /opt/fpp/www/pixeloverlaymodels.php | head -30"),
    ("co-other-modules VirtualMatrix UI", "docker exec fpp-docker sed -n '140,230p' /opt/fpp/www/co-other-modules.php"),
    ("playlist Haruhi_Test", "cat /home/orangepi/fpp/Docker/media/playlists/Haruhi_Test.json 2>/dev/null || cat /home/orangepi/fpp/Docker/media/playlists/Haruhi_Test 2>/dev/null"),
    ("playlist Haruhi_rotate", "cat /home/orangepi/fpp/Docker/media/playlists/Haruhi_rotate.json 2>/dev/null"),
]

for title, cmd in sections:
    print(f"\n{'='*50}\n{title}\n{'='*50}")
    print(host_ssh.run_ssh(cmd, conf=conf)[:8000])
