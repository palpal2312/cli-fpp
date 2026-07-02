"""SSH access to FPP host (Orange Pi) — display rotation, EDID, framebuffer."""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from typing import Any

from cli_fpp.core import project

# Linux fbcon rotation values
ROTATE_MAP = {
    "landscape": 0,
    "portrait-right": 1,
    "portrait-left": 3,
    "inverted": 2,
    # aliases
    "portrait": 1,
    "right": 1,
    "left": 3,
}

ORIENTATION_LABEL = {
    0: "landscape",
    1: "portrait-right",
    2: "inverted",
    3: "portrait-left",
}

# Kernel video=…,rotate=N — sysfs fb0/rotate trên RK356x thường không xoay scanout thật
BOOT_ROTATE_DEGREES = {
    "landscape": 0,
    "portrait-right": 90,
    "portrait-left": 270,
    "inverted": 180,
    "portrait": 90,
    "right": 90,
    "left": 270,
}

BOOT_ENV_PATHS = (
    "/boot/orangepiEnv.txt",
    "/boot/armbianEnv.txt",
)
FPP_DOCKER_NAME = "fpp-docker"
HDMI_CONNECTOR_ID = "114"
HDMI_CRTC_ID = "85"
FPP_COMPOSE_DIR_DEFAULT = "/home/orangepi/fpp/Docker"
FPP_AUTOSTART_SERVICE = "fpp-docker.service"
FPP_AUTOSTART_UNIT_PATH = f"/etc/systemd/system/{FPP_AUTOSTART_SERVICE}"

FPP_DOCKER_SYSTEMD_UNIT = """[Unit]
Description=FPP Docker container (docker-compose)
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={compose_dir}
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose stop
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
"""


@dataclass
class SSHConfig:
    host: str
    user: str
    password: str
    port: int = 22


def get_ssh_config(
    *,
    host: str | None = None,
    user: str | None = None,
    password: str | None = None,
    port: int | None = None,
) -> SSHConfig:
    cfg = project.load_config()
    h = (host or cfg.get("ssh_host") or "").strip()
    if not h:
        # derive from FPP base_url host if set
        try:
            from urllib.parse import urlparse

            h = urlparse(project.get_connection()).hostname or ""
        except ValueError:
            pass
    u = (user or cfg.get("ssh_user") or "orangepi").strip()
    p = password if password is not None else cfg.get("ssh_password", "")
    pt = int(port or cfg.get("ssh_port") or 22)
    if not h:
        raise ValueError(
            "SSH host not configured. Use: config set ssh_host <ip> "
            "or --ssh-host / FPP_SSH_HOST"
        )
    return SSHConfig(host=h, user=u, password=p, port=pt)


def _client(conf: SSHConfig):
    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError(
            "paramiko required for host SSH. Install: pip install paramiko"
        ) from exc
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        conf.host,
        port=conf.port,
        username=conf.user,
        password=conf.password or None,
        timeout=20,
        allow_agent=True,
        look_for_keys=True,
    )
    return client


def run_ssh(command: str, *, conf: SSHConfig | None = None, sudo: bool = False) -> str:
    conf = conf or get_ssh_config()
    if sudo and conf.password:
        command = f"echo {sh_quote(conf.password)} | sudo -S bash -c {sh_quote(command)}"
    client = _client(conf)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=45)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        # strip sudo password prompt noise
        err = re.sub(r"\[sudo\] password for .+?:\s*", "", err)
        return (out + err).strip()
    finally:
        client.close()


def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def _detect_boot_env_path(*, conf: SSHConfig) -> str | None:
    for path in BOOT_ENV_PATHS:
        if run_ssh(f"test -f {sh_quote(path)} && echo yes", conf=conf).strip().endswith("yes"):
            return path
    return None


def _parse_extraargs(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("extraargs="):
            return line.split("=", 1)[1].strip()
    return ""


def _set_video_rotate(extraargs: str, degrees: int) -> str:
    """Insert or replace video=HDMI-A-1:…,rotate=N in extraargs."""
    import re

    parts = [p for p in extraargs.split() if p]
    video_idx = next((i for i, p in enumerate(parts) if p.startswith("video=")), None)
    if degrees == 0:
        if video_idx is not None:
            video = parts[video_idx]
            video = re.sub(r",rotate=\d+", "", video)
            video = re.sub(r",rotate:\d+", "", video)
            if video == "video=":
                parts.pop(video_idx)
            else:
                parts[video_idx] = video
    else:
        video = "video=HDMI-A-1:1920x1080M@60"
        if video_idx is not None:
            video = parts[video_idx]
            video = re.sub(r",rotate=\d+", "", video)
            video = re.sub(r",rotate:\d+", "", video)
        video = f"{video},rotate={degrees}"
        if video_idx is None:
            parts.append(video)
        else:
            parts[video_idx] = video
    return " ".join(parts)


def apply_boot_rotation(mode: str, *, conf: SSHConfig | None = None) -> dict[str, Any]:
    """Patch orangepi/armbian extraargs for kernel DRM rotation (survives reboot)."""
    key = mode.lower().replace("_", "-")
    if key not in BOOT_ROTATE_DEGREES:
        raise ValueError(f"Unknown rotation {mode!r}")
    degrees = BOOT_ROTATE_DEGREES[key]
    conf = conf or get_ssh_config()
    boot_path = _detect_boot_env_path(conf=conf)
    if not boot_path:
        return {"boot_env": None, "degrees": degrees, "skipped": "boot env not found"}
    raw = run_ssh(f"cat {sh_quote(boot_path)}", conf=conf)
    extra = _parse_extraargs(raw)
    new_extra = _set_video_rotate(extra, degrees)
    lines: list[str] = []
    replaced = False
    for line in raw.splitlines():
        if line.startswith("extraargs="):
            lines.append(f"extraargs={new_extra}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"extraargs={new_extra}")
    body = "\n".join(lines) + "\n"
    import base64

    b64 = base64.b64encode(body.encode()).decode()
    run_ssh(
        f"echo {b64} | base64 -d | tee {sh_quote(boot_path)} > /dev/null",
        conf=conf,
        sudo=True,
    )
    return {
        "boot_env": boot_path,
        "degrees": degrees,
        "extraargs": new_extra,
        "reboot_required": degrees != 0 or bool(extra and "rotate=" in extra),
    }


def restart_fpp_container(*, conf: SSHConfig | None = None) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    out = run_ssh(
        f"docker restart {FPP_DOCKER_NAME} 2>&1",
        conf=conf,
        sudo=True,
    )
    return {"container": FPP_DOCKER_NAME, "restart": out.strip().splitlines()[-1] if out else "ok"}


def try_modetest_rotate(degrees: int, *, conf: SSHConfig | None = None) -> dict[str, Any]:
    """Best-effort live DRM rotation (RK356x — thường không hỗ trợ, cần reboot)."""
    if degrees not in (0, 90, 180, 270):
        return {"attempted": False, "reason": f"unsupported degrees {degrees}"}
    conf = conf or get_ssh_config()
    # modetest bản trên Orange Pi không có -r; thử set plane property nếu có
    cmd = f"modetest -M rockchip -w 57:rotation:{degrees} 2>&1"
    out = run_ssh(cmd, conf=conf, sudo=True)
    ok = "failed" not in out.lower() and "invalid argument" not in out.lower() and "usage:" not in out.lower()
    return {"attempted": True, "degrees": degrees, "ok": ok, "output": out[:500]}


def _rotation_warning(status: dict[str, Any]) -> str | None:
    geom = status.get("fb_geometry") or {}
    w, h = geom.get("width"), geom.get("height")
    fb_rotate = status.get("fb_rotate", 0)
    if fb_rotate and w and h and w >= h:
        return (
            "Orange Pi RK356x: sysfs fb_rotate đã ghi nhưng fb_geometry vẫn 1920×1080 — "
            "bình thường nếu chưa reboot sau khi ghi boot video rotate. "
            "Reboot để kernel áp dụng extraargs rotate=90."
        )
    return None

def _parse_edid(raw: bytes) -> dict[str, Any]:
    info: dict[str, Any] = {}
    if len(raw) < 128:
        return info
    mfg = raw[8:10]
    info["manufacturer"] = (
        chr(((mfg[0] >> 2) & 31) + 64)
        + chr((((mfg[0] & 3) << 3) | (mfg[1] >> 5)) + 64)
        + chr((mfg[1] & 31) + 64)
    )
    info["product_id"] = hex(struct.unpack("<H", raw[10:12])[0])
    for i in range(4):
        off = 0x36 + i * 18
        if off + 18 > len(raw) or raw[off : off + 3] != b"\x00\x00\x00":
            continue
        tag = raw[off + 3]
        if tag == 0xFC:
            info["model"] = raw[off + 5 : off + 17].decode("ascii", "replace").strip()
        elif tag == 0xFF:
            info["serial"] = raw[off + 5 : off + 17].decode("ascii", "replace").strip()
    return info


def display_status(*, conf: SSHConfig | None = None) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    rotate_raw = run_ssh("cat /sys/class/graphics/fb0/rotate 2>/dev/null || echo 0", conf=conf)
    try:
        rotate = int(rotate_raw.strip().splitlines()[-1])
    except ValueError:
        rotate = 0
    vsize = run_ssh("cat /sys/class/graphics/fb0/virtual_size 2>/dev/null", conf=conf).strip()
    fbset = run_ssh("fbset -s -fb /dev/fb0 2>/dev/null", conf=conf)
    hdmi = run_ssh("cat /sys/class/drm/card0-HDMI-A-1/status 2>/dev/null", conf=conf).strip()
    geom = re.search(r'geometry\s+(\d+)\s+(\d+)', fbset)
    width = int(geom.group(1)) if geom else None
    height = int(geom.group(2)) if geom else None
    edid_hex = run_ssh("cat /sys/class/drm/card0-HDMI-A-1/edid 2>/dev/null | wc -c", conf=conf)
    edid_info: dict[str, Any] = {}
    try:
        if int(edid_hex.strip()) >= 128:
            import paramiko

            client = _client(conf)
            try:
                _, stdout, _ = client.exec_command(
                    "cat /sys/class/drm/card0-HDMI-A-1/edid", timeout=15
                )
                edid_info = _parse_edid(stdout.read())
            finally:
                client.close()
    except (ValueError, OSError):
        pass
    orientation = ORIENTATION_LABEL.get(rotate, f"rotate-{rotate}")
    logical = "landscape" if width and height and width >= height else "portrait"
    result = {
        "host": conf.host,
        "hdmi_status": hdmi or "unknown",
        "fb_rotate": rotate,
        "orientation": orientation,
        "fb_geometry": {"width": width, "height": height, "virtual_size": vsize},
        "logical_aspect": logical,
        "fbset": fbset,
        "monitor": edid_info,
        "note": (
            "Orange Pi: sysfs /sys/class/graphics/fb0/rotate (fbcon). "
            "RK356x thường không xoay màn thật qua sysfs — dùng boot extraargs "
            "video=HDMI-A-1:1920x1080M@60,rotate=N và reboot."
        ),
    }
    warn = _rotation_warning(result)
    if warn:
        result["warning"] = warn
    return result


def display_rotate(
    mode: str,
    *,
    conf: SSHConfig | None = None,
) -> dict[str, Any]:
    key = mode.lower().replace("_", "-")
    if key not in ROTATE_MAP:
        raise ValueError(
            f"Unknown rotation {mode!r}. Use: {', '.join(sorted(set(ROTATE_MAP)))}"
        )
    value = ROTATE_MAP[key]
    conf = conf or get_ssh_config()
    degrees = BOOT_ROTATE_DEGREES.get(key, 0)
    run_ssh(f"echo {value} > /sys/class/graphics/fb0/rotate", conf=conf, sudo=True)
    boot = apply_boot_rotation(key, conf=conf)
    modetest = try_modetest_rotate(degrees, conf=conf)
    status = display_status(conf=conf)
    status["applied"] = {
        "mode": key,
        "fb_rotate": value,
        "boot_degrees": degrees,
        "boot": boot,
        "modetest": modetest,
    }
    if boot.get("reboot_required"):
        status["reboot_required"] = True
        status["reboot_hint"] = (
            "Chạy reboot Orange Pi để kernel áp dụng video rotate. "
            "Sau reboot: cli-fpp dev host display status"
        )
    return status


SERVICE_NAME = "fpp-fb-rotate.service"
SCRIPT_PATH = "/usr/local/sbin/fpp-fb-rotate.sh"
CONF_PATH = "/etc/fpp-fb-rotate.conf"
UNIT_PATH = f"/etc/systemd/system/{SERVICE_NAME}"

ROTATE_SCRIPT = """#!/bin/bash
set -e
CONF="/etc/fpp-fb-rotate.conf"
if [ -f "$CONF" ]; then
  # shellcheck disable=SC1090
  . "$CONF"
fi
ROTATE="${ROTATE:-0}"
for _ in $(seq 1 60); do
  if [ -e /sys/class/graphics/fb0/rotate ]; then
    echo "$ROTATE" > /sys/class/graphics/fb0/rotate
    exit 0
  fi
  sleep 1
done
echo "fb0 rotate sysfs not available" >&2
exit 1
"""

SYSTEMD_UNIT = """[Unit]
Description=Apply framebuffer rotation for FPP display (fb0)
After=local-fs.target
Wants=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/fpp-fb-rotate.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""


def run_ssh_batch(commands: list[str], *, conf: SSHConfig | None = None, sudo: bool = False) -> str:
    """Single SSH session — faster than many run_ssh() calls."""
    conf = conf or get_ssh_config()
    script = " && ".join(commands)
    return run_ssh(script, conf=conf, sudo=sudo)


def _upload_root_file(path: str, content: str, *, conf: SSHConfig) -> None:
    import base64

    b64 = base64.b64encode(content.encode()).decode()
    run_ssh(
        f"echo {b64} | base64 -d | tee {sh_quote(path)} > /dev/null && chmod 755 {sh_quote(path)}",
        conf=conf,
        sudo=True,
    )


def persist_status(*, conf: SSHConfig | None = None) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    enabled = run_ssh(
        f"systemctl is-enabled {SERVICE_NAME} 2>/dev/null || echo disabled",
        conf=conf,
        sudo=True,
    ).strip().splitlines()[-1]
    active = run_ssh(
        f"systemctl is-active {SERVICE_NAME} 2>/dev/null || echo inactive",
        conf=conf,
        sudo=True,
    ).strip().splitlines()[-1]
    conf_text = run_ssh(f"cat {CONF_PATH} 2>/dev/null || true", conf=conf, sudo=True)
    mode = "unknown"
    rotate = None
    for line in conf_text.splitlines():
        if line.startswith("MODE="):
            mode = line.split("=", 1)[1].strip().strip('"')
        if line.startswith("ROTATE="):
            try:
                rotate = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
    return {
        "service": SERVICE_NAME,
        "enabled": enabled,
        "active": active,
        "config_path": CONF_PATH,
        "mode": mode,
        "fb_rotate": rotate,
    }


def install_display_persist(
    mode: str = "portrait-right",
    *,
    conf: SSHConfig | None = None,
) -> dict[str, Any]:
    key = mode.lower().replace("_", "-")
    if key not in ROTATE_MAP:
        raise ValueError(f"Unknown rotation {mode!r}")
    value = ROTATE_MAP[key]
    conf = conf or get_ssh_config()
    conf_body = f'ROTATE={value}\nMODE="{key}"\n'
    import base64

    files = [
        (CONF_PATH, conf_body),
        (SCRIPT_PATH, ROTATE_SCRIPT),
        (UNIT_PATH, SYSTEMD_UNIT),
    ]
    parts: list[str] = []
    for path, content in files:
        b64 = base64.b64encode(content.encode()).decode()
        parts.append(
            f"echo {b64} | base64 -d | tee {sh_quote(path)} > /dev/null && chmod 755 {sh_quote(path)}"
        )
    parts.append("systemctl daemon-reload")
    parts.append(f"systemctl enable --now {SERVICE_NAME}")
    parts.append(f"echo {value} > /sys/class/graphics/fb0/rotate")
    run_ssh_batch(parts, conf=conf, sudo=True)
    boot = apply_boot_rotation(key, conf=conf)
    modetest = try_modetest_rotate(BOOT_ROTATE_DEGREES[key], conf=conf)
    result = display_status(conf=conf)
    result["applied"] = {
        "mode": key,
        "fb_rotate": value,
        "boot_degrees": BOOT_ROTATE_DEGREES[key],
        "boot": boot,
        "modetest": modetest,
    }
    if boot.get("reboot_required"):
        result["reboot_required"] = True
        result["reboot_hint"] = "Reboot Orange Pi để kernel áp dụng video rotate."
    result["persist"] = {
        "installed": True,
        "service": SERVICE_NAME,
        "mode": key,
        "fb_rotate": value,
        "paths": [CONF_PATH, SCRIPT_PATH, UNIT_PATH],
    }
    return result


def remove_display_persist(*, conf: SSHConfig | None = None) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    run_ssh(
        f"systemctl disable --now {SERVICE_NAME} 2>/dev/null; "
        f"rm -f {UNIT_PATH} {SCRIPT_PATH} {CONF_PATH}; "
        "systemctl daemon-reload",
        conf=conf,
        sudo=True,
    )
    run_ssh("echo 0 > /sys/class/graphics/fb0/rotate", conf=conf, sudo=True)
    status = display_status(conf=conf)
    status["persist"] = {"removed": True, "service": SERVICE_NAME}
    return status


def detect_compose_dir(*, conf: SSHConfig | None = None) -> str:
    """Find docker-compose working dir from running container or default path."""
    conf = conf or get_ssh_config()
    label = run_ssh(
        f"docker inspect {FPP_DOCKER_NAME} "
        "--format '{{index .Config.Labels \"com.docker.compose.project.working_dir\"}}' "
        "2>/dev/null",
        conf=conf,
    ).strip()
    if label and label != "<no value>":
        return label
    if run_ssh(f"test -f {sh_quote(FPP_COMPOSE_DIR_DEFAULT + '/docker-compose.yml')} && echo yes", conf=conf).strip().endswith("yes"):
        return FPP_COMPOSE_DIR_DEFAULT
    return FPP_COMPOSE_DIR_DEFAULT


def fpp_autostart_status(*, conf: SSHConfig | None = None) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    compose_dir = detect_compose_dir(conf=conf)
    docker_enabled = run_ssh(
        "systemctl is-enabled docker.service 2>/dev/null || echo unknown",
        conf=conf,
        sudo=True,
    ).strip().splitlines()[-1]
    docker_active = run_ssh(
        "systemctl is-active docker.service 2>/dev/null || echo unknown",
        conf=conf,
        sudo=True,
    ).strip().splitlines()[-1]
    svc_enabled = run_ssh(
        f"systemctl is-enabled {FPP_AUTOSTART_SERVICE} 2>/dev/null || echo disabled",
        conf=conf,
        sudo=True,
    ).strip().splitlines()[-1]
    svc_active = run_ssh(
        f"systemctl is-active {FPP_AUTOSTART_SERVICE} 2>/dev/null || echo inactive",
        conf=conf,
        sudo=True,
    ).strip().splitlines()[-1]
    restart_policy = run_ssh(
        f"docker inspect {FPP_DOCKER_NAME} --format '{{{{.HostConfig.RestartPolicy.Name}}}}' 2>/dev/null || echo missing",
        conf=conf,
    ).strip()
    container_state = run_ssh(
        f"docker inspect {FPP_DOCKER_NAME} --format '{{{{.State.Status}}}}' 2>/dev/null || echo missing",
        conf=conf,
    ).strip()
    http_code = run_ssh(
        f"curl -s -o /dev/null -w '%{{http_code}}' http://{conf.host}:81/ 2>/dev/null || echo 000",
        conf=conf,
    ).strip()
    return {
        "compose_dir": compose_dir,
        "docker_service": {"enabled": docker_enabled, "active": docker_active},
        "fpp_docker_service": {
            "name": FPP_AUTOSTART_SERVICE,
            "enabled": svc_enabled,
            "active": svc_active,
            "unit_path": FPP_AUTOSTART_UNIT_PATH,
        },
        "container": {
            "name": FPP_DOCKER_NAME,
            "restart_policy": restart_policy,
            "status": container_state,
        },
        "fpp_http": {"port": 81, "code": http_code, "ok": http_code in ("200", "301", "302", "401")},
        "ready": (
            docker_enabled == "enabled"
            and svc_enabled == "enabled"
            and container_state == "running"
        ),
    }


def install_fpp_autostart(
    compose_dir: str | None = None,
    *,
    conf: SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    compose_dir = compose_dir or detect_compose_dir(conf=conf)
    unit_body = FPP_DOCKER_SYSTEMD_UNIT.format(compose_dir=compose_dir)
    import base64

    b64 = base64.b64encode(unit_body.encode()).decode()
    parts = [
        "systemctl enable docker.service",
        f"echo {b64} | base64 -d | tee {sh_quote(FPP_AUTOSTART_UNIT_PATH)} > /dev/null",
        "systemctl daemon-reload",
        f"systemctl enable --now {FPP_AUTOSTART_SERVICE}",
    ]
    run_ssh_batch(parts, conf=conf, sudo=True)
    result = fpp_autostart_status(conf=conf)
    result["installed"] = True
    result["compose_dir"] = compose_dir
    return result


def remove_fpp_autostart(*, conf: SSHConfig | None = None) -> dict[str, Any]:
    conf = conf or get_ssh_config()
    run_ssh(
        f"systemctl disable --now {FPP_AUTOSTART_SERVICE} 2>/dev/null; "
        f"rm -f {FPP_AUTOSTART_UNIT_PATH}; systemctl daemon-reload",
        conf=conf,
        sudo=True,
    )
    result = fpp_autostart_status(conf=conf)
    result["removed"] = True
    return result
