# cli-fpp

Điều khiển [Falcon Player (FPP)](https://github.com/FalconChristmas/fpp) **song song** với web UI — bằng prompt qua AI agents (Cursor, Claude Code, Codex, Gemini, Hermes, OpenClaw, …).

FPP vẫn chạy như bình thường trên Pi/BBB. Bạn vẫn mở `http://fpp.local` để cấu hình playlist, output, schedule. Đồng thời, agent trên PC gọi **cùng REST API** qua `cli-fpp` — không thay thế front-end, không cần SSH vào Pi.

```
                    ┌─────────────────────────────────┐
                    │     FPP instance (fppd)         │
                    │  Web UI  ←→  REST API /api/*    │
                    └────────▲───────────────▲────────┘
                             │               │
              Browser        │               │  HTTP (--json)
         (cấu hình, xem)   │               │
                             │               │
                    ┌────────┴───┐   ┌───────┴────────┐
                    │  Con người  │   │  AI agents     │
                    │  front-end  │   │  + cli-fpp     │
                    └────────────┘   └────────────────┘
```

## Mục tiêu

| Ai dùng | Cách dùng |
|---------|-----------|
| Người | Web UI FPP như hiện tại |
| Agent | `cli-fpp --json …` hoặc REPL; đọc `skills/cli-fpp/SKILL.md` |

Agent và người thao tác **cùng một instance** — thay đổi qua web vẫn thấy qua CLI, và ngược lại.

## Agent {#agent}

Không giới hạn số target — đầy đủ core (media, playlist, schedule, player, multi-target `-t`).

| Bước | Lệnh |
|------|------|
| Onboarding | `agent-harness/cli_fpp/skills/AGENT_ONBOARDING.md` |
| Cài | `pip install -e agent-harness/.[dev]` hoặc `pip install cli-fpp` |
| Kiểm tra | `cli-fpp --json doctor` |
| Skill | `npx skills add palpal2312/cli-fpp --skill cli-fpp -g -y` |
| Python API | `from cli_fpp.core import agent_tools` |

## Cài đặt (máy chạy agent)

```bash
cd agent-harness
pip install -e ".[dev]"
export FPP_BASE_URL=http://fpp.local
cli-fpp ping
```

## Gắn skill cho agent

```bash
# Cursor / Claude Code / các tool hỗ trợ skills
npx skills add palpal2312/cli-fpp --skill cli-fpp -g -y
```

Hoặc trỏ agent đọc `skills/cli-fpp/SKILL.md` trong repo.

## Ví dụ sử dụng

Xem các workflow mẫu trong [`examples/`](./examples/): setup target, điều khiển playlist, upload media, multi-target, và Python `agent_tools`.

## Ví dụ prompt → lệnh

| Prompt (ý người dùng) | Agent chạy |
|------------------------|------------|
| "FPP đang chạy gì?" | `cli-fpp --json player status` (hoặc `system status` nếu API OK) |
| "Play playlist Holiday" | `cli-fpp playlist play Holiday --repeat` |
| "Tắt show nhẹ nhàng" | `cli-fpp playlist stop` |
| "Volume 70" | `cli-fpp command run "Volume Set" 70` |

Luôn dùng `--json` khi agent cần parse kết quả.

## Repo liên quan

| Repo | Vai trò |
|------|---------|
| [palpal2312/fpp](https://github.com/palpal2312/fpp) | Fork FPP (upstream) |
| **cli-fpp** | Agent/CLI client (repo này) |

## Layout

```
cli-fpp/
├── agent-harness/cli_fpp/   # Python package, lệnh `cli-fpp`
├── examples/                # Workflow mẫu theo từng thư mục
└── skills/cli-fpp/SKILL.md  # Hướng dẫn cho agents
```
