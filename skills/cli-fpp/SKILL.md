---
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

### backups
- DELETE `/api/backups/configuration/{Directory}/{BackupFilename}`
- GET `/api/backups/configuration/list/{DeviceName}`
- GET `/api/backups/configuration/list`
- GET `/api/backups/configuration/{Directory}/{BackupFilename}`
- GET `/api/backups/devices`
- GET `/api/backups/list/{DeviceName}`
- GET `/api/backups/list`
- POST `/api/backups/configuration/restore/{Directory}/{BackupFilename}`
- POST `/api/backups/configuration`
- POST `/api/backups/devices/mount/{DeviceName}/{MountLocation}`
- POST `/api/backups/devices/unmount/{DeviceName}/{MountLocation}`

### cape
- GET `/api/cape/eeprom/signingData/{key}/{order}`
- GET `/api/cape/eeprom/signingFile/{key}/{order}`
- GET `/api/cape/options`
- GET `/api/cape/panel/{key}`
- GET `/api/cape/panel`
- GET `/api/cape/strings/{key}`
- GET `/api/cape/strings`
- GET `/api/cape`
- POST `/api/cape/eeprom/sign/{key}/{order}`
- POST `/api/cape/eeprom/signingData`
- POST `/api/cape/eeprom/voucher`

### channel
- DELETE `/api/channel/input/stats`
- GET `/api/channel/input/stats`
- GET `/api/channel/output/processors`
- GET `/api/channel/output/{file}`
- POST `/api/channel/output/processors`
- POST `/api/channel/output/{file}`

### command
- GET `/api/command/{command}`
- POST `/api/command/{command}`
- POST `/api/command`

### commandPresets
- GET `/api/commandPresets/{name}`
- GET `/api/commandPresets`

### commands
- GET `/api/commands/{command}`
- GET `/api/commands`

### configfile
- DELETE `/api/configfile/**`
- GET `/api/configfile/**`
- GET `/api/configfile`
- POST `/api/configfile/**`

### dir
- DELETE `/api/dir/{DirName}/{SubDir}`
- POST `/api/dir/{DirName}/{SubDir}`

### effects
- GET `/api/effects/ALL`
- GET `/api/effects`

### email
- POST `/api/email/configure`
- POST `/api/email/test`

### events
- GET `/api/events/{eventId}/trigger`
- GET `/api/events/{eventId}`
- GET `/api/events`

### file
- DELETE `/api/file/{DirName}/**`
- GET `/api/file/info/{plugin}/{ext}/**`
- GET `/api/file/move/{fileName}`
- GET `/api/file/onUpload/{ext}/**`
- GET `/api/file/{DirName}/**`
- GET `/api/file/{DirName}/tailfollow/*`
- POST `/api/file/{DirName}/copy/{source}/{dest}`
- POST `/api/file/{DirName}/rename/{source}/{dest}`
- POST `/api/file/{DirName}/{Name}`
- POST `/api/file/{DirName}`

### files
- GET `/api/files/zip/{DirNames}`
- GET `/api/files/{DirName}`

### fppd
- DELETE `/api/fppd/e131stats`
- GET `/api/fppd/e131stats`
- GET `/api/fppd/effects`
- GET `/api/fppd/log`
- GET `/api/fppd/mqtt/cache`
- GET `/api/fppd/multiSyncStats`
- GET `/api/fppd/multiSyncSystems`
- GET `/api/fppd/playlist/config`
- GET `/api/fppd/playlist/filetime`
- GET `/api/fppd/playlists`
- GET `/api/fppd/ports/list`
- GET `/api/fppd/ports/pixelCount`
- GET `/api/fppd/ports/stop`
- GET `/api/fppd/ports`
- GET `/api/fppd/schedule`
- GET `/api/fppd/sequence`
- GET `/api/fppd/status`
- GET `/api/fppd/testing/tests/{pattern}`
- GET `/api/fppd/testing/tests`
- GET `/api/fppd/testing`
- GET `/api/fppd/version`
- GET `/api/fppd/volume`
- GET `/api/fppd/warnings_full`
- GET `/api/fppd/warnings`
- POST `/api/fppd/effects/{name}`
- POST `/api/fppd/falcon/hardware`
- POST `/api/fppd/gpio/ext`
- POST `/api/fppd/log/level/{level}`
- POST `/api/fppd/outputs/remap`
- POST `/api/fppd/outputs`
- POST `/api/fppd/playlists/stop`
- POST `/api/fppd/playlists/{name}/item/{item}`
- POST `/api/fppd/playlists/{name}/nextItem`
- POST `/api/fppd/playlists/{name}/prevItem`
- POST `/api/fppd/playlists/{name}/restartItem`
- POST `/api/fppd/playlists/{name}/section/{section}`
- POST `/api/fppd/playlists/{name}/start`
- POST `/api/fppd/playlists/{name}/stop`
- POST `/api/fppd/restart`
- POST `/api/fppd/schedule`
- POST `/api/fppd/sequences/{name}/back`
- POST `/api/fppd/sequences/{name}/pause`
- POST `/api/fppd/sequences/{name}/start`
- POST `/api/fppd/sequences/{name}/step`
- POST `/api/fppd/sequences/{name}/stop`
- POST `/api/fppd/settings/reload/{setting}`
- POST `/api/fppd/settings/reload`
- POST `/api/fppd/shutdown`
- POST `/api/fppd/testing`
- POST `/api/fppd/volume/{volume}`
- PUT `/api/fppd/playlists/{name}/settings`

### git
- GET `/api/git/branches`
- GET `/api/git/originLog`
- GET `/api/git/releases/os/{All}`
- GET `/api/git/releases/sizes`
- GET `/api/git/reset`
- GET `/api/git/status`

### gpio
- GET `/api/gpio/{pin}`
- GET `/api/gpio`
- POST `/api/gpio/{pin}`

### help
- GET `/api/help`

### media
- GET `/api/media/{MediaName}/duration`
- GET `/api/media/{MediaName}/meta`
- GET `/api/media`

### models
- GET `/api/models/{model}`
- GET `/api/models`
- POST `/api/models/raw`
- POST `/api/models`

### network
- DELETE `/api/network/persistentNames`
- GET `/api/network/dns`
- GET `/api/network/gateway`
- GET `/api/network/interface/add/{interface}`
- GET `/api/network/interface/{interface}`
- GET `/api/network/interface`
- GET `/api/network/wifi/scan/{interface}`
- GET `/api/network/wifi/strength`
- POST `/api/network/dns`
- POST `/api/network/gateway`
- POST `/api/network/interface/{interface}/apply`
- POST `/api/network/interface/{interface}`
- POST `/api/network/persistentNames`

### options
- GET `/api/options/{SettingName}`

### overlays
- GET `/api/overlays/effects/{effect}`
- GET `/api/overlays/effects`
- GET `/api/overlays/fonts`
- GET `/api/overlays/model/{model}/clear`
- GET `/api/overlays/model/{model}/data`
- GET `/api/overlays/model/{model}`
- GET `/api/overlays/models`
- GET `/api/overlays/running`
- GET `/api/overlays/settings`
- PUT `/api/overlays/model/{model}/fill`
- PUT `/api/overlays/model/{model}/mmap`
- PUT `/api/overlays/model/{model}/pixel`
- PUT `/api/overlays/model/{model}/save`
- PUT `/api/overlays/model/{model}/state`
- PUT `/api/overlays/model/{model}/text`
- PUT `/api/overlays/range/{ranges}`

### pipewire
- GET `/api/pipewire/control/groups/{id}`
- GET `/api/pipewire/control/groups`
- GET `/api/pipewire/control/input-groups/{id}`
- GET `/api/pipewire/control/input-groups`
- GET `/api/pipewire/control/routing`
- GET `/api/pipewire/control/status`
- GET `/api/pipewire/control/streams`
- POST `/api/pipewire/control/groups/{id}/members/{cardId}/mute`
- POST `/api/pipewire/control/groups/{id}/members/{cardId}/volume`
- POST `/api/pipewire/control/groups/{id}/mute`
- POST `/api/pipewire/control/groups/{id}/volume`
- POST `/api/pipewire/control/input-groups/{id}/members/{memberIndex}/mute`
- POST `/api/pipewire/control/input-groups/{id}/members/{memberIndex}/volume`
- POST `/api/pipewire/control/routing/{inputGroupId}/{outputGroupId}/mute`
- POST `/api/pipewire/control/routing/{inputGroupId}/{outputGroupId}/volume`
- POST `/api/pipewire/control/streams/{slot}/volume`

### player
- GET `/api/player/current`
- GET `/api/player/status`
- GET `/api/player`

### playlist
- DELETE `/api/playlist/{PlaylistName}`
- GET `/api/playlist/{PlaylistName}/start/{Repeat}/{ScheduleProtected}`
- GET `/api/playlist/{PlaylistName}/start/{Repeat}`
- GET `/api/playlist/{PlaylistName}/start`
- GET `/api/playlist/{PlaylistName}`
- POST `/api/playlist/{PlaylistName}/{SectionName}/item`
- POST `/api/playlist/{PlaylistName}`

### playlists
- GET `/api/playlists/pause`
- GET `/api/playlists/playable`
- GET `/api/playlists/resume`
- GET `/api/playlists/stop`
- GET `/api/playlists/stopgracefully`
- GET `/api/playlists/stopgracefullyafterloop`
- GET `/api/playlists/validate`
- GET `/api/playlists`
- POST `/api/playlists`

### plugin
- DELETE `/api/plugin/{RepoName}`
- GET `/api/plugin/headerIndicators`
- GET `/api/plugin/{RepoName}/settings/{SettingName}`
- GET `/api/plugin/{RepoName}/upgrade`
- GET `/api/plugin/{RepoName}`
- GET `/api/plugin`
- POST `/api/plugin/fetchInfo`
- POST `/api/plugin/{RepoName}/settings/{SettingName}`
- POST `/api/plugin/{RepoName}/updates`
- POST `/api/plugin`

### proxies
- DELETE `/api/proxies/{ProxyIp}`
- DELETE `/api/proxies`
- GET `/api/proxies`
- POST `/api/proxies/{ProxyIp}`
- POST `/api/proxies`

### proxy
- GET `/api/proxy/{Ip}/{urlPart}`

### remoteAction
- GET `/api/remoteAction`

### remotes
- GET `/api/remotes`

### schedule
- GET `/api/schedule`
- POST `/api/schedule/reload`
- POST `/api/schedule`

### scripts
- GET `/api/scripts/installRemote/{category}/{filename}`
- GET `/api/scripts/viewRemote/{category}/{filename}`
- GET `/api/scripts/{scriptName}/run`
- GET `/api/scripts/{scriptName}`
- GET `/api/scripts`
- POST `/api/scripts/{scriptName}`

### sequence
- DELETE `/api/sequence/{SequenceName}`
- GET `/api/sequence/current/step`
- GET `/api/sequence/current/stop`
- GET `/api/sequence/current/togglePause`
- GET `/api/sequence/{SequenceName}/meta`
- GET `/api/sequence/{SequenceName}/start/{startSecond}`
- GET `/api/sequence/{SequenceName}`
- GET `/api/sequence`
- POST `/api/sequence/{SequenceName}`

### settings
- GET `/api/settings/{SettingName}`
- GET `/api/settings`
- PUT `/api/settings/{SettingName}/jsonValueUpdate`
- PUT `/api/settings/{SettingName}`

### statistics
- DELETE `/api/statistics/usage`
- GET `/api/statistics/usage`
- POST `/api/statistics/usage`

### system
- GET `/api/system/fppd/restart`
- GET `/api/system/fppd/start`
- GET `/api/system/fppd/stop`
- GET `/api/system/info`
- GET `/api/system/packages/info/{packageName}`
- GET `/api/system/packages`
- GET `/api/system/reboot`
- GET `/api/system/releaseNotes/{version}`
- GET `/api/system/shutdown`
- GET `/api/system/status`
- GET `/api/system/updateStatus`
- GET `/api/system/volume`
- POST `/api/system/fppd/skipBootDelay`
- POST `/api/system/volume`

### testmode
- GET `/api/testmode`
- POST `/api/testmode`

### time
- GET `/api/time`

## Agent onboarding

# cli-fpp — Agent onboarding (một link)

Điều khiển **một màn FPP** qua REST API. Không giới hạn số target. Nhiều màn: lặp `-t` hoặc gọi `agent_tools` từ script/agent bên ngoài.

## 1. Cài trên controller (PC chạy agent)

```bash
pip install -e "agent-harness/.[dev]"   # dev từ repo
# hoặc sau publish: pip install cli-fpp
```

## 2. Kiểm tra môi trường

```bash
cli-fpp doctor --json
```

Top-level `doctor` = controller (Python, git, gh, config). `dev doctor` = SSH/target Orange Pi.

## 3. Thêm target (một cửa hàng / màn)

```bash
cli-fpp target add shop-a --fpp-url http://192.168.1.10:81 --fpp-user admin --fpp-password <secret>
cli-fpp target use shop-a
cli-fpp ping --json
```

## 4. Bắt đầu chiến dịch (một màn)

```bash
cli-fpp suggest "chạy banner Tết trên cửa hàng" --json
cli-fpp guide campaign
```

Luồng điển hình: `media propose` → user OK → `media upload` → `playlist play` → `player current`.

## 5. Skill cho agent

| Cách | Lệnh / path |
|------|-------------|
| Cursor skills | `npx skills add palpal2312/cli-fpp --skill cli-fpp -g -y` |
| Raw repo | `skills/cli-fpp/SKILL.md` hoặc `agent-harness/cli_fpp/skills/SKILL.md` |
| Onboarding | File này (`AGENT_ONBOARDING.md`) |

## 6. Python facade

```python
from cli_fpp.core import agent_tools

agent_tools.list_targets()
agent_tools.suggest("play playlist Holiday")
agent_tools.tool_schema()  # JSON schema cho LLM
```


## Kinh nghiệm thực tế (so sánh UI ↔ API ↔ CLI)

> **Quy tắc duy trì:** Mỗi lần vận hành thật (kết nối, lỗi, câu hỏi user, phát hiện mới) — so sánh với web UI + OpenAPI, rồi **cập nhật file này** trước khi kết thúc session. Chạy `build_skill_md.py` để merge vào SKILL.md.

### Kết nối

| Tình huống | Web UI | API/CLI | Bài học |
|------------|--------|---------|---------|
| User gõ `https://IP:81` | Trình duyệt có thể vẫn mở được tùy redirect | `SSLError: WRONG_VERSION_NUMBER` | Port **81 = HTTP**, dùng `http://192.168.1.39:81` |
| Không auth | Một số trang load | **401** | Luôn `-u admin -p …` hoặc `config set username/password` |
| Lưu cấu hình | — | `cli-fpp config set base_url …` | Không lặp mật khẩu trong prompt; dùng `~/.cli-fpp/config.json` |

### Endpoint tin cậy vs lỗi (instance `192.168.1.39:81`)

| Endpoint | Kết quả thực tế | Thay thế |
|----------|-----------------|----------|
| `GET /api/system/status` | PHP fatal `limonade.php:969` | `player status`, `player current`, `api fppd get-status` |
| `GET /api/playlist/{name}` | Cùng lỗi limonade (một số route) | `player status` → `details` chứa full playlist đang chạy |
| `GET /api/player/status` | **OK** | Ưu tiên cho “đang chạy gì”, global pause, loop |
| `GET /api/player/current` | **OK** | Tóm tắt playlist + `currentEntry` |
| `GET /api/overlays/running` | **OK** (trả `[]` khi không có effect) | — |

### Câu hỏi thường gặp → trường JSON

| User hỏi | Trường trong `player status` | Web UI tương đương |
|----------|------------------------------|-------------------|
| Màn hình đang hiển thị gì? | `currentEntry.type`, `imagePath`, `modelName`, `name` | index.php player widget |
| Playlist nào? | `playlists[].name` hoặc `player current` → `playlist.name` | Playlist dropdown / status bar |
| Global Pause? | `details.globalPauseBetweenSequencesMS` (ms) | playlists.php “Global Pause Between Sequences” |
| Đang lặp vòng mấy? | `loop`, `repeat` | Status / playlist details |
| Pause sequence | `sequence pause` → `togglePause` | Nút Pause trên index.php (không phải `Pause Playlist` command) |
| Dừng playlist | `playlist stop` → REST `stopgracefully` / `stop` | StopGracefully / StopNow trong `fpp.js` |

**Ví dụ đã xác minh** (playlist `Haruhi_Test`):

```bash
cli-fpp --url http://192.168.1.39:81 -u admin -p <secret> --json player status
# globalPauseBetweenSequencesMS: 5000  → Global Pause = 5 giây
# modelName: "FB - fb0"               → framebuffer / màn hình
# type: "image"                       → đang chiếu ảnh, không phải fseq
```

### CLI quirks

| Vấn đề | Cách đúng |
|--------|-----------|
| `--json` sau subcommand | Sai: `api list --json` → **`cli-fpp --json api list`** (`--json` là global flag) |
| HTTPS + cert lỗi | `FPP_VERIFY_SSL=false` (chỉ khi thật sự dùng HTTPS) |
| Mutating API | POST/PUT/DELETE qua `api` → cần confirm hoặc `--yes` / `--dry-run` |
| Mutating SSH host (`sudo`) | Giống API — cần `--yes`; trong Cursor có thể **chờ Approve Smart mode** | Nếu treo lâu (phút/giờ) → thường **đang chờ user Approve**, không phải Orange Pi chậm |
| Tái tạo catalog | `build_skill_md.py` đọc `SKILL_EXPERIENCES.md` — sửa kinh nghiệm ở file đó |

### Front-end → CLI (đã map)

- `fpp.js` `LoadSystemStatus` → `system status` (nếu lỗi → `player status`)
- `ToggleSequencePause` → `sequence pause`
- `StopNow` / `StopGracefully` → `playlist stop [--now]`
- `SetVolume` → `system volume <0-100>`
- `PopulatePlaylists` validate → `playlist list --playable`
- `effects.php` Effect Start → `effects start`
- `pixeloverlaymodels` → `overlays models|running|stop`

### Client vs dev — `suggest` tự phân loại

`cli-fpp suggest "<prompt>" --json` trả `cli_scope` (`client` | `dev`) và `scope_hint`.

| cli_scope | User nói gì | Lệnh |
|-----------|-------------|------|
| **client** | upload ảnh, phát/dừng playlist, volume, trạng thái FPP | `media upload`, `playlist play`, … |
| **dev** | xoay màn, persist, docker autostart, cài/deploy FPP | `dev host …`, `dev fpp install/deploy` |

Agent: đọc `cli_scope` trước khi chạy. `"upload ảnh portrait"` → **client** (không nhầm `dev host rotate`).

### Host SSH — xoay màn vật lý (Orange Pi)

Portrait **không làm trong FPP** — xoay trên host qua `cli-fpp dev host display`:

```bash
cli-fpp config set ssh_host 192.168.1.39
cli-fpp config set ssh_user orangepi
cli-fpp config set ssh_password <secret>
cli-fpp --json --yes dev host display status
cli-fpp --json --yes dev host display rotate portrait-right   # fb_rotate=1
cli-fpp --json --yes dev host display rotate landscape        # fb_rotate=0
```

| Mode | `fb_rotate` | Ghi chú |
|------|-------------|---------|
| `landscape` | 0 | Ngang (mặc định) |
| `portrait-right` / `portrait` | 1 | 90° CW |
| `inverted` | 2 | 180° |
| `portrait-left` | 3 | 90° CCW |

Cơ chế: `echo N | sudo tee /sys/class/graphics/fb0/rotate` trên **Orange Pi RK356x**. EDID đọc từ `card0-HDMI-A-1/edid` (vd. Xiaomi XMI `P27FBA-RAGL`).

**RK356x `192.168.1.39` — cách xoay đúng:**

| Cách | Kết quả |
|------|---------|
| Chỉ `fb0/rotate` sysfs | Ghi được nhưng **chưa xoay màn** ngay |
| `modetest -w 57:rotation:2` | `Invalid argument` (plane primary không hỗ trợ 90°) |
| **Boot `video=HDMI-A-1:1920x1080M@60,rotate=90` + reboot** | **Xoay được** (đã xác minh portrait-right trên Xiaomi P27FBA-RAGL) |

`dev host display rotate portrait-right` / `persist install` tự ghi `orangepiEnv.txt` + sysfs. **Bắt buộc reboot Orange Pi** sau lần đầu. `fb_geometry` có thể vẫn báo 1920×1080 — tin mắt nhìn màn, không chỉ JSON geometry.

```bash
cli-fpp --json --yes dev host display rotate portrait-right
# reboot Orange Pi
cli-fpp --json dev host display status
```

```bash
cli-fpp --json --ssh-host 192.168.1.39 --ssh-user orangepi --ssh-password <secret> --yes dev host display persist install portrait-right
cli-fpp --json --ssh-host 192.168.1.39 --ssh-user orangepi --ssh-password <secret> dev host display persist status
cli-fpp --json --yes dev host display persist remove   # gỡ + về landscape
```

Kết quả `persist status` mong đợi: `enabled: enabled`, `active: active`, `mode: portrait-right`, `fb_rotate: 1`. Cài đặt ~20s (1 phiên SSH batch), không phải hàng chục phút.

| Vấn đề | Nguyên nhân | Cách xử lý |
|--------|-------------|------------|
| `persist install` treo rất lâu | Chờ **Approve** lệnh SSH/sudo trong Cursor; code cũ mở nhiều SSH riêng | Bấm Approve; dùng `--yes`; code dùng `run_ssh_batch` (1 session) |
| `system restart` treo lâu | Cùng lý do approval + FPP restart mất vài phút | Approve sớm; kiểm tra `api fppd get-status` sau |

Files trên host: `/etc/systemd/system/fpp-fb-rotate.service`, `/usr/local/sbin/fpp-fb-rotate.sh`, `/etc/fpp-fb-rotate.conf`

Env: `FPP_SSH_HOST`, `FPP_SSH_USER`, `FPP_SSH_PASSWORD`. Dep: `paramiko`.

### Media upload — auto transpose portrait

FPP **không xoay** ảnh/video trong player (chỉ flip fb0). Portrait signage: **xoay media trước upload** + host `rotate=90`.

CLI tự kiểm tra khung màn qua SSH (`dev host display` / `fb_rotate` / `rotate=` trong cmdline):

```bash
cli-fpp --json media display-profile
cli-fpp --json --yes media upload ./ads/          # auto transpose nếu màn portrait + file dọc
cli-fpp media prepare-images ./src ./out          # rotate=auto (mặc định)
cli-fpp media prepare-videos ./src ./out          # cần ffmpeg local
```

| Điều kiện | Hành vi `rotate=auto` |
|-----------|------------------------|
| Màn landscape | Không transpose |
| Màn portrait + media ngang | Không transpose |
| Màn portrait + media dọc (h>w) | Transpose 90° (portrait-left → 270°) |
| `--no-auto-orient` | Bỏ SSH, chỉ scale theo `--width/--height` |

Ảnh → `images/` (fb0 playlist). Video → `videos/` (VLC/GStreamer; Docker Orange Pi thường lỗi pipewire — xem issue FPP #1027).

### Agent — user đưa ảnh → propose → upload

**Luồng bắt buộc** khi agent nhận ảnh (file hoặc URL):

1. `cli-fpp --json media propose <path-hoặc-url>` — kiểm tra thiết bị + đề xuất xoay
2. Trình bày cho user: host, portrait/landscape, canvas, góc xoay từng ảnh
3. User đồng ý → `cli-fpp --json --yes media upload <cùng nguồn>` (upload tự chạy propose trước)

```bash
cli-fpp --json media propose ./ads/banner.jpg
cli-fpp --json media propose https://example.com/poster.jpg
cli-fpp --json media fetch https://example.com/poster.jpg   # lưu local trước
cli-fpp guide media_upload
```

**JSON `propose` trả về:**

| Trường | Ý nghĩa |
|--------|---------|
| `device.host` | IP/host Orange Pi |
| `device.display_mode` | `portrait` hoặc `landscape` |
| `device.canvas.label` | Khổ fb0 (vd. `1920x1080`) |
| `items[].proposed_rotate_degrees` | `0` / `90` / `270` đề xuất |
| `items[].proposed_reason` | Giải thích |
| `summary` | Tóm tắt một dòng |
| `recommended_cli` | Lệnh upload đề xuất |

| User nói | Agent làm |
|----------|-----------|
| Đính kèm ảnh | Lưu file → `media propose` → chờ OK → `media upload` |
| Gửi link ảnh | `media propose <url>` → chờ OK → `media upload <url>` |
| "Upload và phát X" | propose → upload → `playlist play X` |

### Cursor hooks (tự động)

Project `.cursor/hooks.json` — chạy từ root repo `cli-anything-fpp`:

| Hook | Khi nào | Việc làm |
|------|---------|----------|
| `afterShellExecution` | Lệnh chứa `cli-fpp` / `cli_fpp` | Ghi log → trích insight → append **Nhật ký tự động** → `build_skill_md.py` |
| `afterFileEdit` | Sửa `SKILL_EXPERIENCES.md` | Rebuild `SKILL.md` |
| `stop` | Agent session kết thúc | Rebuild `SKILL.md` |

Script lõi: `agent-harness/scripts/sync_skill_hooks.py`

```bash
python agent-harness/scripts/sync_skill_hooks.py --from-shell "cli-fpp player status" --output "..." --exit 0
```

### Nhật ký tự động (hook)

<!-- AUTO:START -->
<!-- AUTO:END -->

<!-- experiences:auto:begin -->

### Bundled experiences (auto từ JSON)

> Chạy `python agent-harness/scripts/generate_experiences_skill.py` sau khi sửa `experiences_bundled.json`.

#### Global (mọi target)

- **Port 81 = HTTP, không phải HTTPS** `[connection, auth, campaign]`: User gõ https://IP:81 → SSLError WRONG_VERSION_NUMBER. Dùng http://192.168.x.x:81
- **system/status lỗi limonade PHP** `[api, status, campaign]` (override intent=system_status): GET /api/system/status có thể fatal limonade.php trên một số instance. Thay bằng player status, player current, api fppd get-status.
- **Thiếu HTTP auth → 401** `[connection, auth, campaign]`: Luôn cấu hình username/password trong target profile hoặc -u/-p. FPP port 81 thường dùng admin.
- **Chiến dịch màn dọc: transpose trước upload** `[campaign, media, display]`: Portrait signage: media upload --auto-orient + kiểm tra dev host display rotate. FPP không xoay ảnh trong player.
- **QR trên banner creative** `[campaign, media]`: Nhúng QR trong file ảnh creative hoặc FPP Image playlist entry.
- **Schedule giờ cao điểm** `[campaign, schedule]`: Giờ cao điểm: tạo schedule trên web UI → cli-fpp schedule list --json → schedule reload sau khi sửa.
- **Nhiều cửa hàng = nhiều target** `[campaign, connection]`: Mỗi màn một target profile. Lặp lệnh với -t shop-a / -t shop-b hoặc gọi cli-fpp từ script/agent bên ngoài.

#### Device-specific

- **RK356x: xoay màn cần boot rotate=90 + reboot** `[display, ssh, dev, campaign]` (device=orangepi): Chỉ ghi fb0/rotate sysfs thường chưa xoay scanout thật. dev host display rotate/persist ghi orangepiEnv.txt video=...,rotate=90 — bắt buộc reboot Orange Pi sau lần đầu.
- **modetest rotation Invalid argument** `[display, ssh]` (device=orangepi): modetest -w plane rotation 90° có thể Invalid argument trên RK356x. Không dùng — dùng boot rotate trong orangepiEnv.txt.
- **Video trong Docker Orange Pi** `[media, docker, campaign]` (device=orangepi): GStreamer/VLC trong fpp-docker trên Orange Pi hay lỗi pipewire/audio. Ảnh fb0 ổn định hơn video; xem FPP #1027 nếu cần video.
- **Portrait signage: xoay media + host** `[media, display, campaign]` (device=orangepi): FPP không xoay ảnh trong player (chỉ flip fb0). Màn portrait: media upload auto-transpose + dev host display rotate=90.

#### Player-specific (FPP version)

- **Channel output API có thể lỗi PHP** `[api, dev, virtual-matrix]` (player=8.x): /api/channel/output/* đôi khi trả lỗi limonade. Virtual Matrix: ưu tiên SSH sửa co-other.json hoặc cli-fpp dev fpp virtual-matrix set.
- **Virtual Matrix rotate 90/270** `[dev, virtual-matrix]` (player=8.x): Bản FPP gốc chỉ invert/flipHorizontal. Fork palpal2312/fpp thêm rotate 0/90/180/270 trong FBMatrix — cần dev fpp deploy/build trên target.

<!-- experiences:auto:end -->


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
