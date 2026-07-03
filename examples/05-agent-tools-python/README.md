# Ví dụ 05 — Gọi agent_tools từ Python / LLM

`cli_fpp.core.agent_tools` là facade mỏng để agent hoặc script Python gọi trực tiếp, không phải parse stdout của CLI. Nó cũng cung cấp `tool_schema()` dạng JSON để LLM function-calling.

## Chạy nhanh

```bash
python use_agent_tools.py
```

Yêu cầu: đã `pip install -e agent-harness/.[dev]` và có ít nhất một target (xem ví dụ 01).

## Các hàm chính

```python
from cli_fpp.core import agent_tools

agent_tools.list_targets()                       # target đã lưu
agent_tools.audit_targets()                      # version + kết nối
agent_tools.suggest("play playlist Holiday")     # NL → proposed CLI
agent_tools.get_guide("playlist")                # guide theo topic
agent_tools.propose_media(["./creative.jpg"])    # đề xuất trước upload
agent_tools.upload_media("./creative.jpg", target_name="shop-a")
agent_tools.play_playlist("Holiday", repeat=True, target_name="shop-a")
agent_tools.run_doctor()                          # controller health
```

## Tool schema cho LLM

```python
from cli_fpp.core import agent_tools

schema = agent_tools.tool_schema()               # list[dict] JSON schema
result = agent_tools.dispatch_tool(
    "cli_fpp_suggest",
    {"prompt": "chạy playlist Holiday"},
)
```

`dispatch_tool(name, arguments)` chạy một tool theo đúng tên trong schema — tiện cho vòng lặp function-calling của LLM hoặc cho test.
