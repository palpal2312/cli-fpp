# cli-fpp — Ví dụ sử dụng

Mỗi thư mục con là một ví dụ độc lập, chạy được từ máy điều khiển (controller) tới một hoặc nhiều FPP instance qua REST API.

## Chuẩn bị chung

```bash
cd agent-harness
pip install -e ".[dev]"

# Trỏ tới FPP của bạn (một trong hai cách)
export FPP_BASE_URL=http://fpp.local        # hoặc http://192.168.1.10:81
# hoặc dùng target profile:
cli-fpp target add shop-a --fpp-url http://192.168.1.10:81 --fpp-user admin --fpp-password <secret>
cli-fpp target use shop-a
```

Trên Windows PowerShell:

```powershell
$env:FPP_BASE_URL = "http://192.168.1.10:81"
```

## Cú pháp flag toàn cục

`--json`, `--dry-run`, `--yes`, `-t/--target` là option toàn cục của `cli-fpp`, nên đặt trước subcommand:

```bash
cli-fpp --json -t shop-a player status
cli-fpp --json --dry-run playlist play Holiday --repeat
```

## Danh sách ví dụ

| Thư mục | Nội dung |
|---------|----------|
| [`01-single-target-setup`](./01-single-target-setup/) | Thêm một target, kiểm tra kết nối, doctor |
| [`02-player-and-playlist-control`](./02-player-and-playlist-control/) | Xem đang phát gì, play/stop/next playlist |
| [`03-media-upload-workflow`](./03-media-upload-workflow/) | Propose → upload ảnh/video (tự xoay theo màn) |
| [`04-multi-target-operations`](./04-multi-target-operations/) | Chạy cùng lệnh trên nhiều màn với `-t` |
| [`05-agent-tools-python`](./05-agent-tools-python/) | Gọi `cli_fpp.core.agent_tools` từ Python/LLM |

Mỗi ví dụ có `README.md` giải thích và một script chạy được (`.sh` và/hoặc `.py`).
Dùng `--dry-run` để xem trước lệnh mà không gọi FPP, `--json` để agent parse kết quả.
