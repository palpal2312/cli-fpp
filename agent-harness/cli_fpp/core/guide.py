"""Usage guides, intent parsing, and run proposals for agents and humans."""

from __future__ import annotations

import re
from typing import Any, Literal

from cli_fpp.core import experiences as exp_mod

CLI_SCOPE_CLIENT = "client"
CLI_SCOPE_DEV = "dev"
CliScope = Literal["client", "dev"]

SCOPE_HINTS: dict[CliScope, str] = {
    CLI_SCOPE_CLIENT: "Vận hành hàng ngày — FPP API: media, playlist, player, guide.",
    CLI_SCOPE_DEV: "Triển khai / SSH Orange Pi — dev host display, autostart, build (sắp có).",
}

# Topics: CLI help + equivalent FPP web UI path
GUIDES: dict[str, dict[str, Any]] = {
    "start": {
        "title": "Bắt đầu với cli-fpp",
        "summary": "Điều khiển FPP song song với web UI qua REST API.",
        "cli": [
            "export FPP_BASE_URL=http://fpp.local",
            "cli-fpp ping",
            "cli-fpp system status --json",
            "cli-fpp playlist list --json",
        ],
        "web_ui": [
            "Mở trình duyệt: http://<fpp-host>/",
            "Status/Control → xem trạng thái đang phát",
            "Content Manager → Playlists → tạo/sửa playlist",
        ],
        "tips": [
            "Agent nên dùng suggest trước khi chạy lệnh thay đổi trạng thái.",
            "Dùng --dry-run để xem lệnh sẽ gọi API gì mà không thực thi.",
        ],
    },
    "playlist": {
        "title": "Playlist — phát / dừng show",
        "summary": "Quản lý và phát playlist trên FPP.",
        "cli": [
            "cli-fpp playlist list --json",
            "cli-fpp playlist get \"TênPlaylist\" --json",
            "cli-fpp playlist play \"TênPlaylist\" --repeat --json",
            "cli-fpp playlist stop --json",
            "cli-fpp playlist stop --now --json",
        ],
        "web_ui": [
            "Status/Control → Playlists",
            "Chọn playlist → Play (Once / Repeat)",
            "Stop Now / Stop Gracefully trên thanh điều khiển",
        ],
        "tips": [
            "play/stop là thao tác cần confirm trừ khi user đã nói rõ.",
            "Kiểm tra playlist list trước khi play tên user đưa.",
        ],
    },
    "volume": {
        "title": "Âm lượng",
        "summary": "Đặt volume media trên FPP.",
        "cli": [
            "cli-fpp command run \"Volume Set\" 70 --json",
        ],
        "web_ui": [
            "Status/Control → Volume slider",
            "Hoặc Player → điều chỉnh volume khi đang phát",
        ],
        "tips": ["Giá trị volume thường 0–100."],
    },
    "schedule": {
        "title": "Lịch tự động (Schedule)",
        "summary": "Xem và reload lịch phát.",
        "cli": [
            "cli-fpp schedule list --json",
            "cli-fpp schedule reload --json",
        ],
        "web_ui": [
            "Schedule → xem/sửa lịch",
            "Sau khi sửa file lịch: Reload Schedule trên UI hoặc cli-fpp schedule reload",
        ],
        "tips": [],
    },
    "system": {
        "title": "Hệ thống / fppd",
        "summary": "Trạng thái daemon và khởi động lại.",
        "cli": [
            "cli-fpp system status --json",
            "cli-fpp system fppd --json",
            "cli-fpp system restart --json",
        ],
        "web_ui": [
            "System → Status",
            "Menu góc phải → Restart FPPD",
        ],
        "tips": ["restart cần confirm — ảnh hưởng show đang chạy."],
    },
    "display": {
        "title": "Cách hiển thị kết quả",
        "summary": "Đọc preference từ prompt user và format output.",
        "cli": [
            "cli-fpp --json <lệnh>          # JSON cho agent",
            "cli-fpp suggest \"...\" --json   # Kế hoạch có display_preference",
        ],
        "web_ui": [
            "User muốn 'xem trên web' → hướng dẫn mở trang tương ứng, không chỉ chạy CLI",
        ],
        "tips": [
            "json / chi tiết / đầy đủ → format json, detail full",
            "ngắn / tóm tắt / brief → detail brief, tóm tắt text",
            "bảng / table → agent format bảng từ JSON",
        ],
    },
    "media_upload": {
        "title": "Upload ảnh/video — agent nhận file từ user",
        "summary": "User đưa/đính kèm ảnh → agent lưu disk → cli-fpp upload (auto transpose portrait).",
        "cli": [
            "cli-fpp --json media propose <path-hoặc-url>   # BẮT BUỘC trước upload",
            "cli-fpp --json media display-profile",
            "cli-fpp --json media fetch https://... --dest ./.uploads",
            "cli-fpp --json --yes media upload \"<path-hoặc-url>\"",
            "cli-fpp playlist play \"Haruhi_Test\" --repeat --json",
        ],
        "web_ui": [
            "Content Manager → File Manager → images (hoặc videos)",
            "Upload thủ công qua trình duyệt",
            "Playlists → thêm Image entry trỏ model FB - fb0",
        ],
        "tips": [
            "Luồng agent: propose → user xác nhận → upload (không upload thẳng).",
            "propose trả device (host, màn portrait/landscape, canvas), từng ảnh + góc xoay đề xuất.",
            "Nhận ảnh: file đính kèm (lưu workspace) hoặc URL (fetch / propose tải tạm).",
            "Mặc định --auto-orient: SSH kiểm tra màn portrait → transpose ảnh dọc.",
            "Cần config: base_url, username, password, ssh_host.",
        ],
    },
    "campaign": {
        "title": "Chiến dịch quảng cáo — một màn",
        "summary": "Upload creative → playlist → play hoặc schedule → kiểm tra player. Không batch trong CLI.",
        "cli": [
            "cli-fpp target list --json",
            "cli-fpp -t shop-a ping",
            "cli-fpp --json media propose ./banner.jpg",
            "cli-fpp --json --yes media upload ./banner.jpg",
            "cli-fpp playlist list --json",
            'cli-fpp playlist play "Campaign" --repeat --json',
            "cli-fpp player current --json",
            "cli-fpp schedule list --json",
        ],
        "web_ui": [
            "Content Manager → upload ảnh/video creative",
            "Playlists → tạo playlist chiến dịch",
            "Status/Control → Play hoặc Schedule → gán playlist",
            "Status/Control → xem đang phát (player widget)",
        ],
        "tips": [
            "Một target = một màn/cửa hàng. Nhiều màn: lặp `-t` hoặc script/agent gọi cli-fpp từng target.",
            "Portrait signage: media upload auto-transpose + dev host display nếu cần.",
            "QR trên creative: FPP Image entry hoặc overlay.",
            "Giờ cao điểm: schedule list + reload sau khi sửa lịch trên web.",
        ],
    },
    "dev": {
        "title": "Triển khai — group dev (SSH Orange Pi)",
        "summary": "Cài đặt, xoay màn vật lý, Docker autostart — không dùng khi chỉ đổi ảnh/playlist.",
        "cli": [
            "cli-fpp target list",
            "cli-fpp target setup",
            "cli-fpp target catalog",
            "cli-fpp target audit",
            "cli-fpp target add shop-a --fpp-url http://HOST:81 --fpp-user admin --fpp-password ***",
            "cli-fpp target use shop-a",
            "cli-fpp -t shop-a ping",
            "cli-fpp -t shop-a media upload ./banner.jpg",
            "cli-fpp --json dev doctor",
            "cli-fpp --json --yes dev fpp bootstrap --source ../fpp",
            "cli-fpp --json dev fpp status",
            "cli-fpp --json --yes dev fpp deploy --source ../fpp",
            "cli-fpp --json --yes dev fpp build",
            "cli-fpp --json dev fpp virtual-matrix status",
            "cli-fpp --json --yes dev fpp virtual-matrix set --rotate 90",
            "cli-fpp --json --yes dev host display rotate portrait-right",
            "cli-fpp --json --yes dev host display persist install portrait-right",
            "cli-fpp --json dev host fpp autostart status",
            "cli-fpp --json --yes dev host fpp autostart install",
        ],
        "web_ui": [
            "Channel Outputs → Virtual Matrix (invert, flip, rotate)",
            "System → Reboot (sau khi đổi display host)",
        ],
        "tips": [
            "Client nhiều máy: target setup → thông báo số target → thêm (batch/từng cái) → audit FPP version.",
            "Client nhiều máy: target add + -t <name> (hoặc FPP_TARGET) trên mọi lệnh.",
            "Greenfield: target add → dev doctor → dev fpp bootstrap.",
            "Agent: cli_scope=dev khi user nói xoay màn, cài docker, build/deploy FPP.",
            "Đổi ảnh/playlist → cli_scope=client (media upload), không nhầm với dev.",
            "suggest trả cli_scope — agent chỉ chạy dev khi scope=dev.",
        ],
    },
    "experiences": {
        "title": "Kinh nghiệm — theo Target (device) và Player (FPP version)",
        "summary": "Controller ghi nhớ bài học riêng cho từng loại thiết bị và dòng FPP.",
        "cli": [
            "cli-fpp -t shop-a experience list",
            "cli-fpp experience catalog",
            "cli-fpp experience remember \"Portrait RK356x cần reboot sau rotate\"",
            "cli-fpp experience add --scope device --device-type orangepi --title \"...\" --body \"...\"",
            "cli-fpp experience add --scope player --player-line 8.x --title \"...\" --body \"...\"",
        ],
        "web_ui": [],
        "tips": [
            "3 tầng: global (chung) → device (Target) → player (FPP version). Ưu tiên player > device > global.",
            "Bundled: ~/.cli-fpp merge từ experiences_bundled.json (Orange Pi, 8.x, global).",
            "User thêm: experience remember --scope device|player|global.",
            "suggest trả experiences.global / device_specific / player_specific.",
            "Lưu tại ~/.cli-fpp/experiences.json trên controller.",
        ],
    },
}

# Intent keywords (vi + en). Thứ tự quan trọng: rule cụ thể / dev trước.
_INTENT_RULES: list[dict[str, Any]] = [
    {
        "patterns": [
            r"(?:\b(xoay|rotate|quay)\b.*\b(màn|display|màn hình|hdmi|fb0|portrait|landscape|dọc|ngang)\b"
            r"|\b(màn|display|màn hình|hdmi)\b.*\b(xoay|rotate|portrait|landscape|dọc|ngang)\b"
            r"|\bportrait-right\b|\bportrait-left\b)",
        ],
        "unless": [r"\b(upload|tải lên|đưa lên|đẩy lên|ảnh|image|hình)\b.*\b(lên|fpp)\b"],
        "intent": "rotate_display",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda m, _: [
            "cli-fpp --json dev host display status",
            f'cli-fpp --json --yes dev host display rotate {m.get("display_mode", "portrait-right")}',
        ],
        "web_ui": lambda _: [
            "Host: orangepiEnv.txt video=…,rotate=90 + reboot Orange Pi",
            "FPP UI: Channel Outputs → Virtual Matrix (flip/rotate nguồn)",
        ],
    },
    {
        "patterns": [
            r"(?:\b(persist|sau reboot|sau khi khởi động|giữ rotation)\b"
            r"|\b(display|màn)\b.*\b(persist|cố định|sau reboot)\b)",
        ],
        "unless": [r"\b(upload|playlist|ảnh)\b"],
        "intent": "display_persist",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda m, _: [
            f'cli-fpp --json --yes dev host display persist install {m.get("display_mode", "portrait-right")}',
            "cli-fpp --json dev host display persist status",
        ],
        "web_ui": lambda _: ["systemd fpp-fb-rotate.service trên Orange Pi"],
    },
    {
        "patterns": [
            r"(?:\b(autostart|tự chạy|tự khởi động)\b.*\b(docker|fpp|boot)\b"
            r"|\bfpp\b.*\b(autostart|tự chạy)\b)",
        ],
        "intent": "fpp_autostart",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda _m, _: [
            "cli-fpp --json dev host fpp autostart status",
            "cli-fpp --json --yes dev host fpp autostart install",
        ],
        "web_ui": lambda _: ["Docker compose restart:always + systemd fpp-docker.service"],
    },
    {
        "patterns": [
            r"(?:\b(bootstrap|greenfield|cài mới|chưa cài|chưa có)\b.*\b(fpp|docker)\b"
            r"|\b(cài|install)\b.*\b(fpp|docker)\b.*\b(lần đầu|từ đầu|target|thiết bị)\b"
            r"|\bdev doctor\b|\bdev fpp bootstrap\b)",
        ],
        "unless": [r"\b(deploy|patch|upload ảnh|playlist)\b"],
        "intent": "fpp_bootstrap",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda _m, _: [
            "cli-fpp --json dev doctor",
            "cli-fpp --json --yes dev fpp bootstrap --source ../fpp",
            "cli-fpp --json dev doctor",
        ],
        "web_ui": lambda _: ["SSH: upload source + docker-compose + http://HOST:81"],
    },
    {
        "patterns": [
            r"(?:\b(build|deploy|patch|biên dịch)\b.*\b(fpp|fbmatrix|source)\b"
            r"|\b(cài đặt|cài|install)\b.*\b(fpp|docker)\b.*\b(orange|pi|orangepi)\b)",
        ],
        "intent": "fpp_deploy",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda _m, _: [
            "cli-fpp --json dev fpp status",
            "cli-fpp --json --yes dev fpp deploy",
            "cli-fpp --json --yes dev fpp build --target FBMatrix",
        ],
        "web_ui": lambda _: ["SSH + docker cp + restart fpp-docker"],
    },
    {
        "patterns": [
            r"(?:\b(trạng thái|status|orientation|fb_rotate|edid)\b.*\b(màn|display|hdmi|fb0|portrait)\b"
            r"|\b(màn|display)\b.*\b(trạng thái|status|orientation|portrait|landscape)\b"
            r"|\bdev host display status\b)",
        ],
        "unless": [r"\b(upload|playlist|fpp đang chạy|đang phát)\b"],
        "intent": "display_status",
        "scope": CLI_SCOPE_DEV,
        "destructive": False,
        "build_cli": lambda _m, _: [
            "cli-fpp --json dev host display status",
            "cli-fpp --json media display-profile",
        ],
        "web_ui": lambda _: ["Kiểm tra sysfs fb0/rotate + cmdline rotate="],
    },
    {
        "patterns": [
            r"(?:\b(virtual matrix|co-other|fliphorizontal|flip horizontal|invert)\b"
            r"|\bchannel output\b.*\b(flip|invert|rotate)\b)",
        ],
        "intent": "virtual_matrix_config",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda _m, _: [
            "cli-fpp --json dev fpp virtual-matrix status",
            "cli-fpp --json --yes dev fpp virtual-matrix set --rotate 90",
        ],
        "web_ui": lambda _: ["Channel Outputs → co-other.json → Virtual Matrix"],
    },
    {
        "patterns": [r"\b(reboot|khởi động lại)\b.*\b(orange|orangepi|pi|host|máy)\b"],
        "unless": [r"\bfppd\b"],
        "intent": "host_reboot",
        "scope": CLI_SCOPE_DEV,
        "destructive": True,
        "build_cli": lambda _m, _: ["cli-fpp --json --yes system reboot"],
        "web_ui": lambda _: ["System → Reboot (Orange Pi)"],
    },
    {
        "patterns": [
            r"(?:\b(chiến dịch|campaign|quảng cáo|banner|signage|creative)\b"
            r"|\b(chạy|phát|triển khai|deploy|go live|bật)\b.*\b(banner|quảng cáo|chiến dịch|creative|màn hình)\b"
            r"|\b(banner|quảng cáo)\b.*\b(cửa hàng|shop|store|màn hình)\b)",
        ],
        "unless": [
            r"\b(bootstrap|build|patch)\b.*\bfpp\b",
            r"\b(orange|orangepi)\b.*\b(bootstrap|docker|deploy)\b",
            r"\b(upload|tải lên|đưa lên)\b.*\b(ảnh|image)\b",
        ],
        "intent": "run_campaign",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda m, campaign: _build_campaign_cli(m, campaign),
        "web_ui": lambda campaign: [
            "Content Manager → upload creative",
            f"Playlists → play '{campaign}'" if campaign else "Playlists → chọn playlist chiến dịch",
            "Status/Control → xác nhận đang phát",
        ],
    },
    {
        "patterns": [r"\b(status|trạng thái|đang chạy|running)\b"],
        "intent": "system_status",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": False,
        "build_cli": lambda _m, _: ["cli-fpp system status --json"],
        "web_ui": lambda _: ["Mở trang chủ FPP → xem Status/Control"],
    },
    {
        "patterns": [r"\b(play|phát|bật|start)\b|\bplaylist\b"],
        "intent": "play_playlist",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "needs_playlist_name": True,
        "build_cli": lambda m, name: [
            f'cli-fpp playlist play "{name}"' + (" --repeat" if m.get("repeat") else "") + " --json"
        ],
        "web_ui": lambda name: [
            f"Status/Control → Playlists → chọn '{name}' → Play"
            + (" (Repeat)" if True else ""),
        ],
    },
    {
        "patterns": [r"\b(stop|dừng|tắt|ngừng)\b"],
        "intent": "stop_playlist",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "unless": [r"\brestart\b", r"\bfppd\b"],
        "build_cli": lambda m, _: [
            "cli-fpp playlist stop --now --json" if m.get("immediate") else "cli-fpp playlist stop --json"
        ],
        "web_ui": lambda _: ["Status/Control → Stop Now hoặc Stop Gracefully"],
    },
    {
        "patterns": [r"\b(volume|âm lượng|loa)\b"],
        "intent": "set_volume",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda m, _: [f'cli-fpp command run "Volume Set" {m.get("volume", 80)} --json'],
        "web_ui": lambda _: ["Status/Control → kéo thanh Volume"],
    },
    {
        "patterns": [r"\b(list|danh sách|liệt kê)\b.*\bplaylist\b|\bplaylist\b.*\b(list|danh sách)\b"],
        "intent": "list_playlists",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": False,
        "build_cli": lambda _m, _: ["cli-fpp playlist list --json"],
        "web_ui": lambda _: ["Content Manager → Playlists"],
    },
    {
        "patterns": [r"\b(reload|tải lại)\b.*\b(schedule|lịch)\b|\b(schedule|lịch)\b.*\b(reload|tải lại)\b"],
        "intent": "reload_schedule",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda _m, _: ["cli-fpp schedule reload --json"],
        "web_ui": lambda _: ["Schedule → Reload Schedule"],
    },
    {
        "patterns": [r"\b(restart|khởi động lại)\b.*\bfppd\b|\bfppd\b.*\b(restart|khởi động lại)\b"],
        "intent": "restart_fppd",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda _m, _: ["cli-fpp system restart --json"],
        "web_ui": lambda _: ["Menu → Restart FPPD"],
    },
    {
        "patterns": [r"\b(pause|tạm dừng)\b"],
        "intent": "pause_playlist",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda _m, _: ["cli-fpp playlist pause --json"],
        "web_ui": lambda _: ["Status/Control → Pause"],
    },
    {
        "patterns": [r"\b(next|tiếp|skip)\b"],
        "intent": "next_item",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda _m, _: ["cli-fpp playlist next --json"],
        "web_ui": lambda _: ["Status/Control → Next Item"],
    },
    {
        "patterns": [
            r"(?:\b(upload|tải lên|đưa lên|đẩy lên|gửi lên)\b.*\b(ảnh|image|hình|media|video|file)\b"
            r"|\b(ảnh|image|hình|media)\b.*\b(upload|tải lên|đưa lên|đẩy lên)\b"
            r"|\bđính kèm\b.*\b(fpp|màn hình|signage)\b"
            r"|https?://\S+\.(jpg|jpeg|png|webp)\b)",
        ],
        "intent": "upload_media",
        "scope": CLI_SCOPE_CLIENT,
        "destructive": True,
        "build_cli": lambda _m, _: [
            'cli-fpp --json media propose "<path-hoặc-url>"',
            'cli-fpp --json --yes media upload "<path-hoặc-url>"',
        ],
        "web_ui": lambda _: [
            "Content Manager → File Manager → thư mục images",
            "Hoặc để agent: cli-fpp media upload (tự transpose portrait)",
        ],
    },
]

_SCOPE_DEV_SIGNALS: list[str] = [
    r"\bdev host\b",
    r"\bdev fpp\b",
    r"\b(orange\s*pi|orangepi)\b",
    r"\b(xoay|rotate|quay)\b.*\b(màn|display|hdmi|fb0)\b",
    r"\b(màn|display)\b.*\b(xoay|rotate|portrait|landscape)\b",
    r"\b(autostart|docker compose|systemd)\b.*\bfpp\b",
    r"\b(bootstrap|doctor|greenfield)\b.*\bfpp\b",
    r"\b(build|deploy|patch)\b.*\bfpp\b",
    r"\b(virtual matrix|co-other)\b",
    r"\b(reboot|khởi động lại)\b.*\b(orange|orangepi|host|máy)\b",
]

_SCOPE_CLIENT_SIGNALS: list[str] = [
    r"\b(upload|tải lên|đưa lên|đẩy lên)\b",
    r"\b(playlist|phát|play|stop|dừng|pause)\b",
    r"\b(volume|âm lượng)\b",
    r"\b(schedule|lịch)\b",
    r"\bmedia (upload|propose|fetch)\b",
    r"\b(fpp đang chạy|đang phát|trạng thái fpp)\b",
]

_DEV_AGENT_WORKFLOW = [
    "1. cli_scope=dev — chỉ dùng lệnh dev host … / dev fpp …",
    "2. Cần ssh_host trong config hoặc --ssh-host",
    "3. Confirm trước rotate / persist / autostart / reboot",
    "4. Sau đổi display host: reboot Orange Pi",
]

_UPLOAD_AGENT_WORKFLOW = [
    "1. Nhận ảnh: file đính kèm (lưu disk) hoặc URL",
    "2. cli-fpp --json media propose <path-hoặc-url>  — kiểm tra thiết bị, portrait/landscape, đề xuất xoay",
    "3. Trình bày summary + proposed_rotate_degrees cho user",
    "4. User đồng ý → cli-fpp --json --yes media upload <cùng path/URL>",
    "5. (Tuỳ chọn) playlist play <tên>",
]

_CAMPAIGN_AGENT_WORKFLOW = [
    "1. Một màn = một target (-t hoặc default_target)",
    "2. Upload creative: media propose → confirm → media upload",
    "3. Play playlist hoặc schedule — confirm trước play",
    "4. Kiểm tra player current sau go-live",
    "5. Batch nhiều màn: lặp `-t` — cli-fpp không có lệnh batch tích hợp.",
]

_DISPLAY_HINTS: list[tuple[str, str, str]] = [
    (r"\b(json|raw|machine)\b", "json", "full"),
    (r"\b(ngắn|tóm tắt|brief|short)\b", "text", "brief"),
    (r"\b(bảng|table|tabular)\b", "table", "full"),
    (r"\b(chi tiết|đầy đủ|full|detail)\b", "json", "full"),
]


def list_topics() -> list[str]:
    return sorted(GUIDES.keys())


def get_guide(topic: str) -> dict[str, Any]:
    key = topic.lower().strip()
    if key not in GUIDES:
        available = ", ".join(list_topics())
        raise ValueError(f"Unknown topic '{topic}'. Available: {available}")
    return {"topic": key, **GUIDES[key]}


def parse_display_preference(prompt: str) -> dict[str, str]:
    """Infer how the user wants results shown."""
    text = prompt.lower()
    for pattern, fmt, detail in _DISPLAY_HINTS:
        if re.search(pattern, text, re.I):
            return {"format": fmt, "detail": detail}
    return {"format": "json", "detail": "full"}


def _extract_playlist_name(prompt: str) -> str | None:
    # Quoted names first
    m = re.search(r'["\']([^"\']+)["\']', prompt)
    if m:
        return m.group(1).strip()
    # "playlist X" / "play X" (not "chạy gì")
    m = re.search(
        r"(?:playlist|play|phát)\s+([A-Za-z0-9_\-][\w\-]*)",
        prompt,
        re.I,
    )
    if m:
        name = m.group(1).strip()
        if name.lower() not in _INVALID_PLAYLIST_NAMES:
            return name
    return None


_INVALID_PLAYLIST_NAMES = frozenset({"gì", "gi", "what", "nào", "nao", "which"})
_INVALID_CAMPAIGN_NAMES = frozenset(
    {"trên", "lên", "cho", "cửa", "hàng", "store", "shop", "màn", "hình", "màn hình"}
)


def _extract_campaign_name(prompt: str) -> str | None:
    m = re.search(r"banner\s+([A-Za-zÀ-ỹ0-9_\-]+)", prompt, re.I)
    if m:
        name = m.group(1).strip()
        if name.lower() not in _INVALID_CAMPAIGN_NAMES:
            return name
    m = re.search(r"(?:chiến dịch|campaign)\s+([A-Za-zÀ-ỹ0-9_\-]+)", prompt, re.I)
    if m:
        name = m.group(1).strip()
        if name.lower() not in _INVALID_CAMPAIGN_NAMES:
            return name
    return _extract_playlist_name(prompt)


def _build_campaign_cli(flags: dict[str, Any], campaign: str) -> list[str]:
    steps = ["cli-fpp target list --json"]
    steps.extend(
        [
            'cli-fpp --json media propose "<creative-path>"',
            'cli-fpp --json --yes media upload "<creative-path>"',
        ]
    )
    if campaign:
        repeat = " --repeat" if flags.get("repeat") else ""
        steps.append(f'cli-fpp playlist play "{campaign}"{repeat} --json')
    else:
        steps.append("cli-fpp playlist list --json")
    steps.append("cli-fpp player current --json")
    return steps


def _extract_volume(prompt: str) -> int | None:
    m = re.search(r"\b(\d{1,3})\s*%?\b", prompt)
    if m:
        v = int(m.group(1))
        if 0 <= v <= 100:
            return v
    return None


def _extract_display_mode(prompt: str) -> str:
    text = prompt.lower()
    if re.search(r"portrait-left|\bleft\b", text, re.I):
        return "portrait-left"
    if re.search(r"\binverted\b|180|lộn ngược", text, re.I):
        return "inverted"
    if re.search(r"\blandscape\b|ngang", text, re.I):
        return "landscape"
    if re.search(r"\bportrait\b|dọc|portrait-right", text, re.I):
        return "portrait-right"
    return "portrait-right"


def classify_cli_scope(prompt: str, *, intent: str | None = None) -> CliScope:
    """Heuristic client vs dev — dùng khi agent cần biết nhóm lệnh trước khi chạy."""
    text = prompt.lower()
    dev_score = sum(1 for p in _SCOPE_DEV_SIGNALS if re.search(p, text, re.I))
    client_score = sum(1 for p in _SCOPE_CLIENT_SIGNALS if re.search(p, text, re.I))

    dev_intents = {
        "rotate_display",
        "display_persist",
        "display_status",
        "fpp_autostart",
        "fpp_bootstrap",
        "fpp_deploy",
        "virtual_matrix_config",
        "host_reboot",
    }
    if intent in dev_intents:
        return CLI_SCOPE_DEV
    if intent:
        return CLI_SCOPE_CLIENT
    if dev_score > client_score:
        return CLI_SCOPE_DEV
    if client_score > 0:
        return CLI_SCOPE_CLIENT
    return CLI_SCOPE_CLIENT


def _match_intent(prompt: str) -> dict[str, Any] | None:
    text = prompt.lower()
    flags = {
        "repeat": bool(re.search(r"\b(repeat|lặp|lặp lại|loop)\b", text, re.I)),
        "immediate": bool(re.search(r"\b(now|ngay|immediately)\b", text, re.I)),
        "volume": _extract_volume(prompt) or 80,
        "display_mode": _extract_display_mode(prompt),
    }
    name = _extract_playlist_name(prompt)

    for rule in _INTENT_RULES:
        if rule.get("unless"):
            if any(re.search(p, text, re.I) for p in rule["unless"]):
                continue
        if not all(re.search(p, text, re.I) for p in rule["patterns"]):
            continue
        if rule.get("needs_playlist_name") and not name:
            continue
        if rule["intent"] == "play_playlist" and not name:
            continue
        if rule["intent"] == "set_volume" and _extract_volume(prompt) is None:
            if not re.search(r"\b(volume|âm lượng)\b", text, re.I):
                continue
        if rule["intent"] == "run_campaign":
            campaign = _extract_campaign_name(prompt) or ""
            cli_cmds = rule["build_cli"](flags, campaign)
            web = rule["web_ui"](campaign)
            extracted: dict[str, Any] = {}
            if campaign:
                extracted["campaign"] = campaign
            return {
                "intent": rule["intent"],
                "scope": rule.get("scope", CLI_SCOPE_CLIENT),
                "destructive": rule["destructive"],
                "proposed_cli": cli_cmds,
                "proposed_web_ui": web,
                "extracted": extracted,
            }
        cli_cmds = rule["build_cli"](flags, name or "")
        web = rule["web_ui"](name or "")
        return {
            "intent": rule["intent"],
            "scope": rule.get("scope", CLI_SCOPE_CLIENT),
            "destructive": rule["destructive"],
            "proposed_cli": cli_cmds,
            "proposed_web_ui": web,
            "extracted": {k: v for k, v in {"playlist": name, "volume": flags.get("volume"), "display_mode": flags.get("display_mode")}.items() if v},
        }
    return None


def _apply_suggest_overrides(matched: dict[str, Any], *, target_name: str | None = None) -> dict[str, Any]:
    override = exp_mod.suggest_override_for_intent(intent=matched["intent"], target_name=target_name)
    if not override:
        return matched
    cli = override.get("proposed_cli") or override.get("replace_cli")
    if not cli:
        use_cli = override.get("use_cli")
        if use_cli:
            cmd = use_cli.strip()
            cli = [cmd if cmd.startswith("cli-fpp") else f"cli-fpp {cmd} --json"]
    if isinstance(cli, str):
        cli = [cli]
    if not cli:
        return matched
    updated = dict(matched)
    updated["proposed_cli"] = list(cli)
    if override.get("experience_id"):
        updated["experience_override_applied"] = override["experience_id"]
    return updated


def _attach_experiences(result: dict[str, Any], *, target_name: str | None = None) -> dict[str, Any]:
    ctx = exp_mod.get_context(target_name=target_name)
    result["target_context"] = ctx
    result["experiences"] = exp_mod.experiences_for_suggest(target_name=target_name)
    result["experience_priority"] = exp_mod.PRIORITY_HINT
    return result


def suggest(prompt: str, *, target_name: str | None = None) -> dict[str, Any]:
    """Parse natural-language prompt → display prefs, confirmation, CLI + web proposals."""
    display = parse_display_preference(prompt)
    matched = _match_intent(prompt)
    if matched:
        matched = _apply_suggest_overrides(matched, target_name=target_name)

    if not matched:
        scope = classify_cli_scope(prompt)
        result = {
            "user_prompt": prompt,
            "understood": False,
            "cli_scope": scope,
            "scope_hint": SCOPE_HINTS[scope],
            "display_preference": display,
            "message": (
                "Chưa nhận diện được ý rõ. "
                f"Gợi ý scope: {scope} — {SCOPE_HINTS[scope]} "
                "Hoặc: cli-fpp guide <topic>"
            ),
            "confirmation_required": False,
            "suggested_topics": list_topics(),
            "example_prompts": [
                'play playlist "Holiday" lặp lại, hiển thị json',
                "dừng show nhẹ nhàng",
                "upload ảnh này lên FPP",
                "xoay màn portrait trên Orange Pi",
                "cài fpp docker autostart khi boot",
            ],
        }
        return _attach_experiences(result, target_name=target_name)

    destructive = matched["destructive"]
    intent = matched["intent"]
    scope = matched.get("scope") or classify_cli_scope(prompt, intent=intent)
    confirm_msg = _confirmation_message(intent, matched.get("extracted", {}))

    if intent == "upload_media":
        agent_workflow = list(_UPLOAD_AGENT_WORKFLOW)
    elif intent == "run_campaign":
        agent_workflow = list(_CAMPAIGN_AGENT_WORKFLOW)
    elif scope == CLI_SCOPE_DEV:
        agent_workflow = list(_DEV_AGENT_WORKFLOW)
    else:
        agent_workflow = [
            "1. Gọi suggest với prompt user",
            "2. Trình bày proposed_cli + proposed_web_ui theo display_preference",
            "3. Hỏi confirm nếu confirmation_required",
            "4. Chạy lệnh với --yes sau khi user đồng ý",
        ]

    result = {
        "user_prompt": prompt,
        "understood": True,
        "interpreted_intent": intent,
        "cli_scope": scope,
        "scope_hint": SCOPE_HINTS[scope],
        "display_preference": display,
        "extracted": matched.get("extracted", {}),
        "confirmation_required": destructive,
        "confirmation_prompt": confirm_msg if destructive else None,
        "proposed_cli": matched["proposed_cli"],
        "proposed_web_ui": matched["proposed_web_ui"],
        "how_to_run": {
            "via_cli": (
                "Sau khi user confirm: chạy proposed_cli (thêm --yes nếu đã confirm, hoặc --dry-run để xem trước)"
            ),
            "via_web": "User có thể làm tương đương trên web UI theo proposed_web_ui",
            "parallel": "CLI và web UI dùng chung fppd — chọn một hoặc cả hai",
        },
        "agent_workflow": agent_workflow,
    }
    if matched.get("experience_override_applied"):
        result["experience_override_applied"] = matched["experience_override_applied"]
    return _attach_experiences(result, target_name=target_name)


def _confirmation_message(intent: str, extracted: dict[str, Any]) -> str:
    if intent == "run_campaign":
        return "Triển khai creative lên màn signage (upload + play)?"
    if intent == "upload_media":
        return "Upload ảnh/video lên FPP (tự transpose nếu màn portrait)?"
    if intent == "rotate_display":
        mode = extracted.get("display_mode", "portrait-right")
        return f"Xoay màn host sang '{mode}' qua SSH (Orange Pi)?"
    if intent == "display_persist":
        mode = extracted.get("display_mode", "portrait-right")
        return f"Cài persist rotation '{mode}' sau reboot?"
    if intent == "fpp_autostart":
        return "Cài systemd để FPP docker tự chạy khi boot?"
    if intent == "fpp_bootstrap":
        return "Bootstrap FPP trên target (upload source + docker + build)?"
    if intent == "fpp_deploy":
        return "Build/deploy FPP lên Orange Pi?"
    if intent == "host_reboot":
        return "Reboot Orange Pi? Show sẽ gián đoạn."
    if intent == "virtual_matrix_config":
        return "Sửa Virtual Matrix (flip/rotate) trên FPP?"
    if intent == "play_playlist":
        name = extracted.get("playlist", "?")
        return f"Bạn có muốn phát playlist '{name}' trên FPP không?"
    if intent == "stop_playlist":
        return "Bạn có muốn dừng playlist đang chạy không?"
    if intent == "set_volume":
        v = extracted.get("volume", "?")
        return f"Đặt âm lượng thành {v}%?"
    if intent == "restart_fppd":
        return "Khởi động lại fppd? Show hiện tại có thể bị gián đoạn."
    if intent == "reload_schedule":
        return "Reload lịch phát từ file cấu hình?"
    return "Thực hiện thao tác này trên FPP?"
