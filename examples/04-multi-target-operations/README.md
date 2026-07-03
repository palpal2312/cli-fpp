# Ví dụ 04 — Vận hành nhiều target

Ví dụ này dùng nhiều target profile đã lưu và chạy cùng một workflow trên từng FPP instance bằng `-t`.

## Chuẩn bị target

```bash
cli-fpp target add shop-a --fpp-url http://192.168.1.10:81 --fpp-user admin --fpp-password <secret>
cli-fpp target add shop-b --fpp-url http://192.168.1.11:81 --fpp-user admin --fpp-password <secret>
cli-fpp --json target list
cli-fpp --json target audit
```

## Chạy nhanh

```bash
./run-on-targets.sh Holiday shop-a shop-b
```

Script sẽ:

1. Ping từng target.
2. Xem player status từng target.
3. Dry-run lệnh play playlist.
4. Chạy play thật với `--yes`.
5. Kiểm tra `player current`.

## Lệnh mẫu

```bash
cli-fpp --json -t shop-a player status
cli-fpp --json -t shop-b player status
cli-fpp --json --yes -t shop-a playlist play Holiday --repeat
cli-fpp --json --yes -t shop-b playlist play Holiday --repeat
```

## Ghi chú

- `cli-fpp` không giới hạn số target; cứ lặp `-t <name>` ở tầng script/agent.
- Với nhiều target, nên ghi log per target và retry riêng target lỗi.
- Nếu chỉ cần audit version/connectivity, dùng `cli-fpp --json target audit`.
