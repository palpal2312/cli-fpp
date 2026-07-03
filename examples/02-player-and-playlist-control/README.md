# Ví dụ 02 — Điều khiển player và playlist

Ví dụ này minh họa các thao tác thường ngày: xem FPP đang phát gì, liệt kê playlist, phát một playlist, chuyển item, rồi dừng.

## Chạy nhanh

```bash
./control-playlist.sh Holiday
```

Hoặc chỉ xem trước, không gọi FPP:

```bash
cli-fpp --json --dry-run playlist play Holiday --repeat
cli-fpp --json --dry-run playlist stop --now
```

## Lệnh chính

```bash
cli-fpp --json player status
cli-fpp --json player current
cli-fpp --json playlist list --playable
cli-fpp --json playlist play Holiday --repeat
cli-fpp --json playlist next
cli-fpp --json playlist stop --now
```

## Ghi chú cho agent

- Ưu tiên `player status` khi user hỏi “đang chạy gì?”.
- Với thao tác thay đổi trạng thái phát, dùng `--dry-run` trước nếu cần trình bày kế hoạch cho user.
- Thêm `--yes` sau khi user đã xác nhận để bỏ prompt confirm.
