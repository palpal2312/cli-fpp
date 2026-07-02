"""Install, deploy, build FPP Docker on Orange Pi host via SSH."""

from __future__ import annotations

import json
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from cli_fpp.core import host_ssh

FPP_IMAGE = "falconchristmas/fpp:latest"
FPP_UID = 500
FPP_GID = 500

SOURCE_TREE_DIRS = ("src", "www")

DEFAULT_DEPLOY_REL_PATHS = (
    "src/channeloutput/FBMatrix.cpp",
    "src/channeloutput/FBMatrix.h",
    "www/co-other-modules.php",
)

BUILD_TARGETS = {
    "FBMatrix": "libfpp-co-FBMatrix.so",
    "all": "",
}


def resolve_fpp_source(explicit: Path | str | None = None) -> Path:
    """Locate local FPP git tree (env FPP_SOURCE or sibling ../fpp)."""
    if explicit:
        root = Path(explicit).resolve()
        if not (root / "src" / "channeloutput" / "FBMatrix.cpp").is_file():
            raise ValueError(f"Not an FPP source tree: {root}")
        return root

    env = os.environ.get("FPP_SOURCE", "").strip()
    if env:
        root = Path(env).resolve()
        if (root / "src" / "channeloutput" / "FBMatrix.cpp").is_file():
            return root
        raise ValueError(f"FPP_SOURCE invalid: {env}")

    here = Path(__file__).resolve()
    for base in [Path.cwd(), *Path.cwd().parents, here.parents[3], here.parents[4]]:
        cand = (base / "fpp").resolve()
        if (cand / "src" / "channeloutput" / "FBMatrix.cpp").is_file():
            return cand
    raise ValueError(
        "FPP source not found. Set FPP_SOURCE, pass --source, or clone fpp/ next to workspace."
    )


def _compose_dir(compose_dir: str | None, *, conf: host_ssh.SSHConfig) -> str:
    return compose_dir or host_ssh.detect_compose_dir(conf=conf)


def _media_dir(compose_dir: str) -> str:
    return f"{compose_dir.rstrip('/')}/media"


def _co_other_path(compose_dir: str) -> str:
    return f"{_media_dir(compose_dir)}/config/co-other.json"


def _container_config_path() -> str:
    return "/home/fpp/media/config/co-other.json"


def write_host_text(
    remote_path: str,
    content: str,
    *,
    conf: host_ssh.SSHConfig | None = None,
    mode: str = "644",
    sudo: bool = False,
) -> None:
    import base64

    conf = conf or host_ssh.get_ssh_config()
    parent = remote_path.rsplit("/", 1)[0]
    if parent:
        host_ssh.run_ssh(f"mkdir -p {host_ssh.sh_quote(parent)}", conf=conf)
    b64 = base64.b64encode(content.encode()).decode()
    host_ssh.run_ssh(
        f"echo {b64} | base64 -d | tee {host_ssh.sh_quote(remote_path)} > /dev/null "
        f"&& chmod {mode} {host_ssh.sh_quote(remote_path)}",
        conf=conf,
        sudo=sudo,
    )


def upload_host_file(
    local_path: Path | str,
    remote_path: str,
    *,
    conf: host_ssh.SSHConfig | None = None,
) -> None:
    conf = conf or host_ssh.get_ssh_config()
    local_path = Path(local_path)
    parent = remote_path.rsplit("/", 1)[0]
    host_ssh.run_ssh(f"mkdir -p {host_ssh.sh_quote(parent)}", conf=conf)
    client = host_ssh._client(conf)
    try:
        sftp = client.open_sftp()
        sftp.put(str(local_path), remote_path)
    finally:
        client.close()


def render_compose_yaml(
    *,
    host_ip: str,
    http_port: int = 81,
    mount_source: bool = False,
    timezone: str = "Asia/Ho_Chi_Minh",
) -> str:
    """docker-compose for Orange Pi signage (fb0 + HTTP on host port)."""
    lines = [
        "version: '3'",
        "services:",
        "  fpp-docker:",
        f"    container_name: {host_ssh.FPP_DOCKER_NAME}",
        f"    image: {FPP_IMAGE}",
        "    restart: always",
        f"    hostname: {host_ssh.FPP_DOCKER_NAME}",
        "    volumes:",
        "      - ./media:/home/fpp/media",
    ]
    if mount_source:
        lines.append("      - ./fpp:/opt/fpp")
    lines.extend(
        [
            "    environment:",
            f"      - FPP_DOCKER_IP={host_ip}",
            f"      - TZ={timezone}",
            "    cap_add:",
            "      - SYS_PTRACE",
            "      - SYS_NICE",
            "    devices:",
            "      - /dev/fb0",
            "      - /dev/dri/card0",
            "      - /dev/dri/renderD128",
            "    ports:",
            f'      - "{host_ip}:{http_port}:80/tcp"',
            f'      - "{host_ip}:4048:4048/udp"',
            f'      - "{host_ip}:5568:5568/udp"',
            f'      - "{host_ip}:32320:32320/udp"',
            "",
        ]
    )
    return "\n".join(lines)


def fpp_status(
    *,
    compose_dir: str | None = None,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    compose_file = f"{compose_dir}/docker-compose.yml"
    has_compose = host_ssh.run_ssh(
        f"test -f {host_ssh.sh_quote(compose_file)} && echo yes",
        conf=conf,
    ).strip().endswith("yes")
    has_media = host_ssh.run_ssh(
        f"test -d {host_ssh.sh_quote(_media_dir(compose_dir))} && echo yes",
        conf=conf,
    ).strip().endswith("yes")
    image = host_ssh.run_ssh(
        f"docker images -q {FPP_IMAGE} 2>/dev/null | head -1",
        conf=conf,
    ).strip()
    autostart = host_ssh.fpp_autostart_status(conf=conf)
    vm = virtual_matrix_status(compose_dir=compose_dir, conf=conf, restart=False)
    return {
        "compose_dir": compose_dir,
        "compose_file": compose_file,
        "has_compose": has_compose,
        "has_media": has_media,
        "image_pulled": bool(image),
        "image": FPP_IMAGE,
        **autostart,
        "virtual_matrix": vm.get("virtual_matrix"),
    }


def fpp_install(
    *,
    compose_dir: str | None = None,
    http_port: int = 81,
    mount_source: bool = False,
    pull: bool = True,
    autostart: bool = True,
    force: bool = False,
    timezone: str = "Asia/Ho_Chi_Minh",
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = compose_dir or host_ssh.FPP_COMPOSE_DIR_DEFAULT
    compose_file = f"{compose_dir}/docker-compose.yml"
    if not force:
        exists = host_ssh.run_ssh(
            f"test -f {host_ssh.sh_quote(compose_file)} && echo yes",
            conf=conf,
        ).strip().endswith("yes")
        if exists:
            raise ValueError(
                f"{compose_file} already exists. Use --force to overwrite or omit install."
            )

    media = _media_dir(compose_dir)
    cmds = [
        f"mkdir -p {host_ssh.sh_quote(compose_dir)}",
        f"mkdir -p {host_ssh.sh_quote(media)}/config",
        f"mkdir -p {host_ssh.sh_quote(media)}/logs",
        f"mkdir -p {host_ssh.sh_quote(media)}/uploads",
        f"mkdir -p {host_ssh.sh_quote(media)}/images",
        f"mkdir -p {host_ssh.sh_quote(media)}/videos",
        f"chown -R {FPP_UID}:{FPP_GID} {host_ssh.sh_quote(media)}",
    ]
    if mount_source:
        cmds.append(f"mkdir -p {host_ssh.sh_quote(compose_dir)}/fpp")
    host_ssh.run_ssh_batch(cmds, conf=conf, sudo=True)

    body = render_compose_yaml(
        host_ip=conf.host,
        http_port=http_port,
        mount_source=mount_source,
        timezone=timezone,
    )
    write_host_text(compose_file, body, conf=conf)

    steps = []
    if pull:
        out = host_ssh.run_ssh(
            f"cd {host_ssh.sh_quote(compose_dir)} && docker-compose pull",
            conf=conf,
            sudo=True,
        )
        steps.append({"pull": out.splitlines()[-3:]})
    up = host_ssh.run_ssh(
        f"cd {host_ssh.sh_quote(compose_dir)} && docker-compose up -d",
        conf=conf,
        sudo=True,
    )
    steps.append({"up": up.splitlines()[-5:]})

    result = fpp_status(compose_dir=compose_dir, conf=conf)
    result["installed"] = True
    result["steps"] = steps
    result["http_url"] = f"http://{conf.host}:{http_port}/"

    if autostart:
        result["autostart"] = host_ssh.install_fpp_autostart(compose_dir, conf=conf)
    return result


def fpp_pull(
    *,
    compose_dir: str | None = None,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    out = host_ssh.run_ssh(
        f"cd {host_ssh.sh_quote(compose_dir)} && docker-compose pull",
        conf=conf,
        sudo=True,
    )
    return {"compose_dir": compose_dir, "pull": out}


def fpp_up(
    *,
    compose_dir: str | None = None,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    out = host_ssh.run_ssh(
        f"cd {host_ssh.sh_quote(compose_dir)} && docker-compose up -d",
        conf=conf,
        sudo=True,
    )
    return {"compose_dir": compose_dir, "up": out, **fpp_status(compose_dir=compose_dir, conf=conf)}


def _sync_config_to_container(compose_dir: str, *, conf: host_ssh.SSHConfig) -> None:
    path = _co_other_path(compose_dir)
    host_ssh.run_ssh(
        f"docker cp {host_ssh.sh_quote(path)} "
        f"{host_ssh.FPP_DOCKER_NAME}:{host_ssh.sh_quote(_container_config_path())}",
        conf=conf,
        sudo=True,
    )


def _find_virtual_matrix_output(data: dict[str, Any]) -> dict[str, Any] | None:
    outputs = data.get("channelOutputs") or []
    for item in outputs:
        if str(item.get("type", "")).lower() == "virtualmatrix":
            return item
    return None


def virtual_matrix_status(
    *,
    compose_dir: str | None = None,
    conf: host_ssh.SSHConfig | None = None,
    restart: bool = False,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    path = _co_other_path(compose_dir)
    raw = host_ssh.run_ssh(f"cat {host_ssh.sh_quote(path)} 2>/dev/null", conf=conf)
    if not raw.strip():
        return {"compose_dir": compose_dir, "path": path, "found": False}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"compose_dir": compose_dir, "path": path, "found": False, "error": str(exc)}
    vm = _find_virtual_matrix_output(data)
    return {
        "compose_dir": compose_dir,
        "path": path,
        "found": vm is not None,
        "virtual_matrix": vm,
    }


def virtual_matrix_set(
    *,
    compose_dir: str | None = None,
    invert: bool | None = None,
    flip_horizontal: bool | None = None,
    rotate: int | None = None,
    width: int | None = None,
    height: int | None = None,
    device: str | None = None,
    restart_container: bool = True,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    path = _co_other_path(compose_dir)
    status = virtual_matrix_status(compose_dir=compose_dir, conf=conf)
    if not status.get("found"):
        data: dict[str, Any] = {
            "channelOutputs": [
                {
                    "enabled": 1,
                    "type": "VirtualMatrix",
                    "startChannel": 1,
                    "channelCount": 6220800,
                    "modelName": "",
                    "invert": False,
                    "flipHorizontal": False,
                    "rotate": 0,
                    "device": device or "fb0",
                    "width": width or 1920,
                    "height": height or 1080,
                }
            ]
        }
    else:
        raw = host_ssh.run_ssh(f"cat {host_ssh.sh_quote(path)}", conf=conf)
        data = json.loads(raw)

    vm = _find_virtual_matrix_output(data)
    if vm is None:
        raise ValueError("co-other.json has no VirtualMatrix output")

    if invert is not None:
        vm["invert"] = bool(invert)
    if flip_horizontal is not None:
        vm["flipHorizontal"] = bool(flip_horizontal)
    if rotate is not None:
        if rotate not in (0, 90, 180, 270):
            raise ValueError("rotate must be 0, 90, 180, or 270")
        vm["rotate"] = int(rotate)
    if width is not None:
        vm["width"] = int(width)
    if height is not None:
        vm["height"] = int(height)
    if device is not None:
        vm["device"] = device

    w = int(vm.get("width") or 1920)
    h = int(vm.get("height") or 1080)
    vm["channelCount"] = w * h * 3

    body = json.dumps(data, indent="\t") + "\n"
    write_host_text(path, body, conf=conf)
    _sync_config_to_container(compose_dir, conf=conf)

    restart_info = None
    if restart_container:
        restart_info = host_ssh.restart_fpp_container(conf=conf)

    return {
        "path": path,
        "virtual_matrix": vm,
        "synced": True,
        "restart": restart_info,
    }


def fpp_build(
    *,
    target: str = "FBMatrix",
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    make_target = BUILD_TARGETS.get(target, target)
    if target == "all":
        cmd = "cd /opt/fpp/src && make -j$(nproc) 2>&1"
    else:
        cmd = f"cd /opt/fpp/src && make {make_target} 2>&1"
    out = host_ssh.run_ssh(
        f"docker exec {host_ssh.FPP_DOCKER_NAME} bash -lc {host_ssh.sh_quote(cmd)}",
        conf=conf,
        sudo=True,
    )
    ok = "No rule to make" not in out and "Error" not in out[-500:]
    return {
        "target": target,
        "make_target": make_target or "all",
        "ok": ok,
        "output_tail": out[-4000:],
    }


def fpp_deploy(
    *,
    source: Path | str | None = None,
    files: list[str] | None = None,
    compose_dir: str | None = None,
    build: bool = True,
    build_target: str = "FBMatrix",
    restart_container: bool = True,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    root = resolve_fpp_source(source)
    rel_paths = list(files) if files else list(DEFAULT_DEPLOY_REL_PATHS)

    staging = f"/tmp/cli-fpp-deploy-{os.getpid()}"
    host_ssh.run_ssh(f"rm -rf {host_ssh.sh_quote(staging)} && mkdir -p {host_ssh.sh_quote(staging)}", conf=conf)

    deployed: list[dict[str, str]] = []
    for rel in rel_paths:
        local = (root / rel).resolve()
        if not local.is_file():
            raise FileNotFoundError(f"Missing source file: {local}")
        remote = f"{staging}/{rel}"
        upload_host_file(local, remote, conf=conf)
        container_path = f"/opt/fpp/{rel.replace(chr(92), '/')}"
        host_ssh.run_ssh(
            f"docker cp {host_ssh.sh_quote(remote)} "
            f"{host_ssh.FPP_DOCKER_NAME}:{host_ssh.sh_quote(container_path)}",
            conf=conf,
            sudo=True,
        )
        deployed.append({"local": str(local), "container": container_path})

    build_result = None
    if build:
        build_result = fpp_build(target=build_target, conf=conf)

    restart_info = None
    if restart_container:
        restart_info = host_ssh.restart_fpp_container(conf=conf)

    host_ssh.run_ssh(f"rm -rf {host_ssh.sh_quote(staging)}", conf=conf)

    return {
        "source": str(root),
        "compose_dir": compose_dir,
        "deployed": deployed,
        "build": build_result,
        "restart": restart_info,
    }


def upload_fpp_source_tree(
    source: Path | str,
    remote_fpp_dir: str,
    *,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    """Đẩy thư mục src/ + www/ từ FPP local lên host (cho mount ./fpp:/opt/fpp)."""
    conf = conf or host_ssh.get_ssh_config()
    root = resolve_fpp_source(source)
    uploaded_dirs: list[str] = []

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tar_path = Path(tmp.name)
    try:
        with tarfile.open(tar_path, "w:gz") as tar:
            for name in SOURCE_TREE_DIRS:
                local_dir = root / name
                if not local_dir.is_dir():
                    raise FileNotFoundError(f"Missing {local_dir}")
                tar.add(local_dir, arcname=name)
                uploaded_dirs.append(name)

        remote_tar = f"/tmp/cli-fpp-source-{os.getpid()}.tar.gz"
        upload_host_file(tar_path, remote_tar, conf=conf)
        host_ssh.run_ssh(
            f"rm -rf {host_ssh.sh_quote(remote_fpp_dir)} && "
            f"mkdir -p {host_ssh.sh_quote(remote_fpp_dir)} && "
            f"tar xzf {host_ssh.sh_quote(remote_tar)} -C {host_ssh.sh_quote(remote_fpp_dir)} && "
            f"rm -f {host_ssh.sh_quote(remote_tar)}",
            conf=conf,
        )
    finally:
        tar_path.unlink(missing_ok=True)

    return {
        "source": str(root),
        "remote_dir": remote_fpp_dir,
        "dirs": uploaded_dirs,
    }


def fpp_down(
    *,
    compose_dir: str | None = None,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    """docker-compose down — dừng container FPP trên target."""
    conf = conf or host_ssh.get_ssh_config()
    compose_dir = _compose_dir(compose_dir, conf=conf)
    out = host_ssh.run_ssh(
        f"cd {host_ssh.sh_quote(compose_dir)} && docker-compose down",
        conf=conf,
        sudo=True,
    )
    return {"compose_dir": compose_dir, "down": out}


def fpp_bootstrap(
    *,
    source: Path | str | None = None,
    compose_dir: str | None = None,
    http_port: int = 81,
    build: bool = True,
    build_target: str = "FBMatrix",
    autostart: bool = True,
    down_first: bool = False,
    conf: host_ssh.SSHConfig | None = None,
) -> dict[str, Any]:
    """
    Greenfield: doctor → upload FPP source → install (mount source) → build → up/restart.

    Dùng khi target chưa có FPP Docker hoặc cần cài lại từ source local.
    """
    from cli_fpp.core import dev_target

    conf = conf or host_ssh.get_ssh_config()
    compose_dir = compose_dir or host_ssh.FPP_COMPOSE_DIR_DEFAULT
    remote_fpp = f"{compose_dir.rstrip('/')}/fpp"

    before = dev_target.dev_doctor(compose_dir=compose_dir, conf=conf)
    steps: list[dict[str, Any]] = [{"doctor_before": before}]

    if down_first:
        steps.append({"down": fpp_down(compose_dir=compose_dir, conf=conf)})

    steps.append({"upload_source": upload_fpp_source_tree(source, remote_fpp, conf=conf)})

    install_result = fpp_install(
        compose_dir=compose_dir,
        http_port=http_port,
        mount_source=True,
        pull=True,
        autostart=autostart,
        force=True,
        conf=conf,
    )
    steps.append({"install": install_result})

    build_result = None
    if build:
        build_result = fpp_build(target=build_target, conf=conf)
        steps.append({"build": build_result})

    restart = host_ssh.restart_fpp_container(conf=conf)
    steps.append({"restart": restart})

    after = dev_target.dev_doctor(compose_dir=compose_dir, conf=conf)
    steps.append({"doctor_after": after})

    return {
        "workflow": [
            "1. dev doctor — kiểm tra target",
            "2. upload FPP source (src/, www/) lên host",
            "3. dev fpp install --mount-source (docker pull + up)",
            "4. make plugin trong container (patch rotate)",
            "5. restart + doctor",
        ],
        "compose_dir": compose_dir,
        "http_url": f"http://{conf.host}:{http_port}/",
        "ready": after.get("ready", False),
        "steps": steps,
    }
