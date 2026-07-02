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

