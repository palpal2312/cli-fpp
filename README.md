# cli-fpp

Command-line client for [Falcon Player (FPP)](https://github.com/FalconChristmas/fpp).

**Đây là repo độc lập**, không phải fork của FPP hay CLI-Anything. Chỉ wrap REST API của FPP; thiết kế tham khảo [CLI-Anything HARNESS](https://github.com/HKUDS/CLI-Anything).

| Repo | Vai trò |
|------|---------|
| [palpal2312/fpp](https://github.com/palpal2312/fpp) | Fork FPP (upstream C++/PHP) |
| **cli-fpp** (repo này) | Python CLI client, chạy trên PC |
| [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) | Methodology tham khảo (không fork) |

## Cài đặt

```bash
cd agent-harness
pip install -e ".[dev]"
export FPP_BASE_URL=http://fpp.local
cli-fpp ping
```

## Contribute lên FPP

FPP team thường chấp nhận:
- Link tool bên ngoài trong `docs/`
- Hoặc thư mục `tools/cli-fpp/` nếu muốn bundle

Không merge Python client vào core `fppd` — FPP đã chuyển sang REST API thay cho CLI `fpp` cũ.

## Layout

```
cli-fpp/
├── agent-harness/cli_fpp/   # Python package
└── skills/cli-fpp/SKILL.md  # Agent skill (optional)
```
