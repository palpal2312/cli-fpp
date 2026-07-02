#!/usr/bin/env python3
"""Generate SKILL.md from FPP openapi.json."""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "agent-harness"
GENERATE_EXP = HARNESS / "scripts" / "generate_experiences_skill.py"
ONBOARDING = HARNESS / "cli_fpp" / "skills" / "AGENT_ONBOARDING.md"

if GENERATE_EXP.exists():
    subprocess.run([sys.executable, str(GENERATE_EXP)], check=True)

OPENAPI = ROOT.parent / "fpp" / "www" / "api" / "openapi.json"
if not OPENAPI.exists():
    import os

    env_path = os.environ.get("FPP_OPENAPI", "").strip()
    if env_path:
        OPENAPI = Path(env_path)
if not OPENAPI.exists():
    raise SystemExit(f"openapi.json not found: {OPENAPI}")

with OPENAPI.open(encoding="utf-8") as f:
    spec = json.load(f)

by_tag: dict[str, list[str]] = defaultdict(list)
for path, ops in spec.get("paths", {}).items():
    for method, op in ops.items():
        if method in ("get", "post", "put", "delete", "patch") and isinstance(op, dict):
            for t in op.get("tags", ["?"]):
                by_tag[t].append(f"{method.upper()} `{path}`")

catalog_lines: list[str] = []
for tag in sorted(by_tag):
    catalog_lines.append(f"### {tag}")
    for line in sorted(set(by_tag[tag]), key=str.lower):
        catalog_lines.append(f"- {line}")
    catalog_lines.append("")
catalog_text = "\n".join(catalog_lines)

header = """---
name: cli-fpp
description: Control FPP via REST API in parallel with web UI. Full API catalog (217 paths). Guide, suggest, confirm, execute.
---

# cli-fpp — Agent Skill

Nguồn: FPP OpenAPI `www/api/openapi.json` — **253 operations**, **217 paths**, **38 tag groups**.

## Kết nối

```bash
cli-fpp config set base_url http://fpp.local:81
cli-fpp config set username admin
cli-fpp config set password <secret>
```

Env: `FPP_BASE_URL`, `FPP_USER`, `FPP_PASSWORD`. Flags: `--url`, `--user`, `--password`, `--json`, `--dry-run`, `--yes`.

**Onboarding một link:** `agent-harness/cli_fpp/skills/AGENT_ONBOARDING.md` — pip install, doctor, target add, campaign suggest.

**Doctor:** `cli-fpp doctor` (controller) vs `cli-fpp dev doctor` (SSH/target).

**Orchestration:** `cli_fpp.core.agent_tools` — list_targets, upload_media, play_playlist, suggest, tool_schema().

Docs live: `{base}/api/` · OpenAPI: `{base}/api/openapi.json`

## Workflow agent

1. `cli-fpp suggest "<prompt>" --json` — ý định, display, CLI + web, confirm
2. Trình bày theo `display_preference` (json / brief / table)
3. Confirm nếu `confirmation_required`
4. `cli-fpp --yes <cmd> --json` hoặc `--dry-run`

## cli-fpp đã wrap

**253/253 operations** — mỗi endpoint OpenAPI có lệnh CLI qua nhóm `api`:

```bash
cli-fpp api list                    # liệt kê tất cả
cli-fpp api list --tag fppd         # theo tag
cli-fpp api fppd get-status         # GET /api/fppd/status
cli-fpp api configfile get gpio.json
cli-fpp api call <op_id> --path '{}' --body '{}'
```

Lệnh thân thiện (alias front-end):

| Lệnh | REST |
|------|------|
| `ping` | GET `/api/system/status` |
| `player status/current` | `/api/player/*` |
| `system status/info/fppd/volume/restart/reboot` | `/api/system/*` |
| `playlist list/get/play/stop/next/prev/pause` | playlists + commands |
| `sequence pause/step/stop` | `/api/sequence/current/*` |
| `media list/sequences/duration` | `/api/media`, `/api/sequence` |
| `media display-profile/propose/fetch/prepare-images/upload` | SSH auto-orient + POST `/api/file/{dir}/{name}` |
| `effects list/running/start/stop` | effects + commands |
| `overlays models/running/stop` | `/api/overlays/*` |
| `gpio list/get/set` | `/api/gpio/*` |
| `dev host display status/rotate/persist` | SSH host `fb0/rotate` + systemd `fpp-fb-rotate.service` |
| `command list/help/run/presets` | `/api/command*` |
| `schedule list/reload/extend/next` | `/api/schedule` |
| `guide`, `suggest`, `config` | — |

Tái tạo khi FPP cập nhật OpenAPI: `python agent-harness/scripts/build_api_wrap.py`

## Ưu tiên khi user hỏi

| Câu hỏi | API | cli-fpp |
|---------|-----|---------|
| Đang chạy gì | GET `/api/fppd/status`, `/api/player/current` | `system fppd` (hoặc REST) |
| Trạng thái | GET `/api/system/status` | `system status` |
| List playlist | GET `/api/playlists` | `playlist list` |
| Phát | command hoặc `/api/playlist/{Name}/start/{Repeat}` | `playlist play` |
| Dừng | `/api/playlists/stopgracefully` | `playlist stop` |
| Volume | `/api/fppd/volume/{n}` hoặc command | `command run "Volume Set" n` |
| Media | GET `/api/media` | `media list` / `media upload` (agent: user đưa ảnh) |
| GPIO | GET/POST `/api/gpio/{pin}` | REST |
| Overlay | `/api/overlays/*` | REST |

## Command API

- POST `/api/command` — `{"command":"Name","args":[]}`
- GET `/api/command/{command}/arg1/arg2`
- POST `/api/command/{command}` — body JSON array args
- GET `/api/commands`, `/api/commands/{command}`
- GET `/api/commandPresets`, `/api/commandPresets/{name}`

## REST khi cần endpoint cụ thể

```bash
cli-fpp api list --tag network
cli-fpp api network get-interface eth0
cli-fpp api call fppd__get-status
```

## Tag groups (tóm tắt)

| Tag | Mục đích |
|-----|----------|
| backups | Backup/restore config, mount devices |
| cape | Cape hardware, panel, strings |
| channel | Output processors, input stats |
| command/commands/commandPresets | FPP commands |
| configfile | JSON config files |
| dir/file/files | Media file I/O |
| effects | Effects list |
| email | Email config |
| events | Event triggers |
| fppd | Daemon control (status, playlist, sequence, volume, log, test, multisync) |
| git | FPP git update |
| gpio | GPIO |
| help | API index |
| media | Media list/meta |
| models | Pixel models |
| network | DNS, WiFi, interfaces |
| options | Setting metadata |
| overlays | Overlay models/effects |
| pipewire | Audio routing |
| player | Player status |
| playlist/playlists | Playlist CRUD & transport |
| plugin | Plugins |
| proxies/proxy/remotes | Multi-FPP |
| schedule | Schedules |
| scripts | Scripts |
| sequence | Sequences |
| settings | settings.json |
| statistics | Usage stats |
| system | OS, reboot, packages |
| testmode | Test mode |
| time | System time |

## Toàn bộ endpoints theo tag

"""

EXPERIENCES_FILE = ROOT / "agent-harness" / "cli_fpp" / "skills" / "SKILL_EXPERIENCES.md"

footer = """
## Quy tắc agent

1. `--json` khi parse; đọc display từ prompt
2. `suggest` + confirm trước play/stop/restart/reboot/upload
3. Luôn đề xuất cách làm trên web UI song song CLI
4. Non-TTY: `--yes` hoặc `--dry-run`
5. Auth HTTP Basic nếu proxy yêu cầu (401)
6. Plugin routes: `/api/plugin/{RepoName}/...`
7. **User đưa/đính kèm ảnh:** `media propose` trước → user OK → `media upload` (xem `guide media_upload`)
8. **Sau mỗi session thực tế:** so sánh UI/API/CLI → cập nhật `SKILL_EXPERIENCES.md` rồi chạy `build_skill_md.py`

## Upstream

- https://github.com/FalconChristmas/fpp
- https://github.com/palpal2312/cli-fpp
"""

experiences = ""
if EXPERIENCES_FILE.exists():
    experiences = "\n" + EXPERIENCES_FILE.read_text(encoding="utf-8").strip() + "\n\n"

onboarding = ""
if ONBOARDING.exists():
    onboarding = (
        "\n## Agent onboarding\n\n"
        + ONBOARDING.read_text(encoding="utf-8").strip()
        + "\n\n"
    )

out = header + catalog_text + onboarding + experiences + footer
targets = [
    ROOT / "agent-harness" / "cli_fpp" / "skills" / "SKILL.md",
    ROOT / "skills" / "cli-fpp" / "SKILL.md",
]
for t in targets:
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(out, encoding="utf-8")
    print("wrote", t, len(out), "chars")
