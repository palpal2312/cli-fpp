# cli-fpp — Agent onboarding (một link)

Điều khiển **một màn FPP** qua REST API. Không giới hạn số target. Nhiều màn: lặp `-t` hoặc gọi `agent_tools` từ script/agent bên ngoài.

## 1. Cài trên controller (PC chạy agent)

```bash
pip install -e "agent-harness/.[dev]"   # dev từ repo
# hoặc sau publish: pip install cli-fpp
```

## 2. Kiểm tra môi trường

```bash
cli-fpp --json doctor
```

Top-level `doctor` = controller (Python, git, gh, config). `dev doctor` = SSH/target Orange Pi.

## 3. Thêm target (một cửa hàng / màn)

```bash
cli-fpp target add shop-a --fpp-url http://192.168.1.10:81 --fpp-user admin --fpp-password <secret>
cli-fpp target use shop-a
cli-fpp --json ping
```

## 4. Bắt đầu chiến dịch (một màn)

```bash
cli-fpp --json suggest "chạy banner Tết trên cửa hàng"
cli-fpp guide campaign
```

Luồng điển hình: `media propose` → user OK → `media upload` → `playlist play` → `player current`.

## 5. Skill cho agent

| Cách | Lệnh / path |
|------|-------------|
| Cursor skills | `npx skills add palpal2312/cli-fpp --skill cli-fpp -g -y` |
| Raw repo | `skills/cli-fpp/SKILL.md` hoặc `agent-harness/cli_fpp/skills/SKILL.md` |
| Onboarding | File này (`AGENT_ONBOARDING.md`) |

## 6. Python facade

```python
from cli_fpp.core import agent_tools

agent_tools.list_targets()
agent_tools.suggest("play playlist Holiday")
agent_tools.tool_schema()  # JSON schema cho LLM
```
