# Ví dụ 03 — Workflow upload media

Ví dụ này chạy workflow an toàn cho ảnh/video: propose hướng xử lý, upload, rồi kiểm tra danh sách media.

## Khi nào dùng

- Upload ảnh/video từ máy local hoặc URL lên FPP.
- Màn portrait cần xoay/transpose media trước khi upload.
- Agent cần trình bày đề xuất cho user trước khi thực hiện.

## Chạy nhanh

```bash
./upload-media-workflow.sh ./creative.jpg
```

Dùng URL:

```bash
./upload-media-workflow.sh https://example.com/banner.jpg
```

## Lệnh chính

```bash
cli-fpp --json media propose ./creative.jpg
cli-fpp --json --dry-run media upload ./creative.jpg
cli-fpp --json --yes media upload ./creative.jpg
cli-fpp --json media list
```

## Tùy chọn hữu ích

```bash
# Bỏ tự xoay nếu media đã được chuẩn bị đúng kích thước/hướng
cli-fpp --json --yes media upload ./ready.mp4 --no-auto-orient

# Chỉ chuẩn bị ảnh local ra thư mục build/ không upload
cli-fpp --json media prepare-images ./input ./build --width 1080 --height 1920 --rotate auto --overwrite
```

## Ghi chú

- `media propose` không upload; chỉ đọc profile màn và metadata media để đưa đề xuất.
- `media upload` mặc định chạy propose trước, hỏi xác nhận, rồi mới upload.
- Với agent, nên hiển thị summary từ `propose` trước khi chạy lệnh thật.
