# Đóng góp kinh nghiệm sử dụng (field experiences)

Thư mục này nhận kinh nghiệm từ người dùng `cli-fpp` trên máy thật, sau khi maintainer review sẽ merge vào `experiences_bundled.json`.

## Luồng người dùng

1. Dùng CLI bình thường — lỗi, audit, `experience remember` tự ghi vào `~/.cli-fpp/contrib_queue.jsonl`
2. `cli-fpp doctor` — kiểm tra gh/git/config
3. `cli-fpp experience contribute login` — `gh auth login` (web browser)
4. `cli-fpp experience contribute submit --github` — fork + PR tự động
5. Hoặc `submit --repo PATH` — ghi file inbox local nếu đã clone repo

## Luồng maintainer

```bash
python agent-harness/scripts/merge_contributions.py --dry-run
python agent-harness/scripts/merge_contributions.py --apply
```

Script dedupe theo fingerprint, gợi ý entry mới cho bundled, không tự xóa inbox (review thủ công).

## Quyền riêng tư

- Mặc định bật (`contrib_enabled: true` trong config). Tắt: `CLI_FPP_CONTRIB=0` hoặc `config set contrib_enabled false`
- IP, password, user được redact trước khi lưu queue
- Export đánh dấu `anonymous: true` — không gửi hostname hay credential

## Schema

File inbox: `cli-fpp-contribution/v1` — xem `experience_contrib.SCHEMA_VERSION`.
