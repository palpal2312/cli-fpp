# Ví dụ 01 — Thiết lập một target FPP

Ví dụ này lưu một FPP instance thành target profile, chọn làm mặc định, rồi kiểm tra kết nối.

## Khi nào dùng

- Lần đầu cấu hình `cli-fpp` trên máy chạy agent.
- Muốn quản lý FPP bằng tên dễ nhớ như `shop-a`, `lobby`, `demo-screen`.
- Muốn tránh truyền `--url`, `--user`, `--password` ở mọi lệnh.

## Chạy nhanh

```bash
./setup-single-target.sh shop-a http://192.168.1.10:81 admin '<secret>'
```

PowerShell có thể chạy từng lệnh tương đương:

```powershell
cli-fpp target add shop-a --fpp-url http://192.168.1.10:81 --fpp-user admin --fpp-password <secret> --default
cli-fpp target use shop-a
cli-fpp --json ping
cli-fpp --json doctor
```

## Kết quả mong đợi

- `cli-fpp --json target list` hiển thị target mới.
- `cli-fpp --json ping` trả kết quả kết nối tới FPP.
- `cli-fpp --json config show` không lộ password thật; secret được mask.
