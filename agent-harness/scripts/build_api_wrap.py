#!/usr/bin/env python3
"""Generate OpenAPI registry + CLI from fpp/www/api/openapi.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT.parent.parent / "fpp" / "www" / "api" / "openapi.json"
if not OPENAPI.exists():
    import os

    env_path = os.environ.get("FPP_OPENAPI", "").strip()
    if env_path:
        OPENAPI = Path(env_path)
if not OPENAPI.exists():
    raise SystemExit(f"openapi.json not found: {OPENAPI}")

OUT_REGISTRY = ROOT / "cli_fpp" / "core" / "openapi_registry.py"
OUT_CLI = ROOT / "cli_fpp" / "cli_openapi.py"

METHODS = ("get", "post", "put", "delete", "patch")


def _slug(s: str) -> str:
    s = re.sub(r"\{[^}]+\}", "", s)
    s = s.replace("/**", "").replace("/*", "").replace("**", "").replace("*", "")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.strip("/"))
    s = re.sub(r"_+", "_", s).strip("_").lower()
    return s or "root"


def _cli_name(method: str, path: str, tag: str) -> str:
  prefix = f"/api/{tag}/"
  if path.startswith(prefix):
      rest = path[len(prefix) :]
  elif path.startswith("/api/"):
      rest = path[5:]
  else:
      rest = path
  rest = rest.replace("/**", "-wildcard").replace("/*", "-tail").replace("{", "").replace("}", "")
  rest = re.sub(r"[^a-zA-Z0-9]+", "-", rest).strip("-").lower()
  name = f"{method}-{rest}" if rest else method
  name = re.sub(r"-+", "-", name)
  return name[:80]


def _parse_operations(spec: dict) -> list[dict]:
    ops: list[dict] = []
    seen: dict[str, int] = {}
    seen_cli: dict[tuple[str, str], int] = {}
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method not in METHODS or not isinstance(op, dict):
                continue
            tag = (op.get("tags") or ["misc"])[0]
            cli_name = _cli_name(method, path, tag)
            ck = (tag, cli_name)
            cn = seen_cli.get(ck, 0)
            seen_cli[ck] = cn + 1
            if cn:
                cli_name = f"{cli_name}-{cn}"
            base_id = f"{tag}__{_cli_name(method, path, tag)}"
            n = seen.get(base_id, 0)
            seen[base_id] = n + 1
            op_id = base_id if n == 0 else f"{base_id}__{n}"
            path_params = []
            query_params = []
            for p in op.get("parameters", []):
                if p.get("in") == "path":
                    path_params.append(p["name"])
                elif p.get("in") == "query":
                    query_params.append(p["name"])
            for p in methods.get("parameters", []):
                if isinstance(p, dict) and p.get("in") == "path" and p["name"] not in path_params:
                    path_params.append(p["name"])
            if "/**" in path:
                path_params.append("_wildcard")
            elif "/*" in path or path.endswith("*"):
                path_params.append("_tail")
            ops.append(
                {
                    "id": op_id,
                    "method": method.upper(),
                    "path": path,
                    "tag": tag,
                    "cli_name": cli_name,
                    "summary": (op.get("summary") or op_id).replace('"', "'"),
                    "path_params": path_params,
                    "query_params": query_params,
                    "mutating": method in ("post", "put", "delete", "patch"),
                }
            )
    return ops


def _gen_registry(ops: list[dict]) -> str:
    lines = [
        '"""AUTO-GENERATED from build_api_wrap.py — do not edit."""',
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Any",
        "",
        "from cli_fpp.utils import fpp_backend as api",
        "",
        "",
        "@dataclass(frozen=True)",
        "class Operation:",
        "    id: str",
        "    method: str",
        "    path: str",
        "    tag: str",
        "    cli_name: str",
        "    summary: str",
        "    path_params: tuple[str, ...]",
        "    query_params: tuple[str, ...]",
        "    mutating: bool",
        "",
        "",
        "OPERATIONS: dict[str, Operation] = {",
    ]
    for op in ops:
        lines.append(f'    "{op["id"]}": Operation(')
        lines.append(f'        id="{op["id"]}",')
        lines.append(f'        method="{op["method"]}",')
        lines.append(f'        path="{op["path"]}",')
        lines.append(f'        tag="{op["tag"]}",')
        lines.append(f'        cli_name="{op["cli_name"]}",')
        lines.append(f'        summary="{op["summary"][:120]}",')
        lines.append(f"        path_params={tuple(op['path_params'])!r},")
        lines.append(f"        query_params={tuple(op['query_params'])!r},")
        lines.append(f"        mutating={op['mutating']!r},")
        lines.append("    ),")
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def _build_path(template: str, path_values: dict[str, str]) -> str:")
    lines.append('    """Substitute {param} and handle /** wildcards."""')
    lines.append("    path = template")
    lines.append('    if "/**" in path and "_wildcard" in path_values:')
    lines.append('        wc = path_values["_wildcard"].lstrip("/")')
    lines.append('        path = path.replace("/**", "/" + wc if wc else "")')
    lines.append('    elif "/*" in path and "_tail" in path_values:')
    lines.append('        tail = path_values["_tail"].lstrip("/")')
    lines.append('        path = path.replace("/*", "/" + tail if tail else "")')
    lines.append("    for key, val in path_values.items():")
    lines.append('        if key.startswith("_"):')
    lines.append("            continue")
    lines.append('        path = path.replace("{" + key + "}", api.quote_segment(str(val)))')
    lines.append("    return path")
    lines.append("")
    lines.append("")
    lines.append("def execute(")
    lines.append("    op_id: str,")
    lines.append("    *,")
    lines.append("    path_values: dict[str, str] | None = None,")
    lines.append("    query: dict[str, Any] | None = None,")
    lines.append("    body: Any | None = None,")
    lines.append("    base_url: str | None = None,")
    lines.append(") -> Any:")
    lines.append('    """Execute a registered OpenAPI operation by id."""')
    lines.append("    op = OPERATIONS[op_id]")
    lines.append("    path_values = path_values or {}")
    lines.append("    endpoint = _build_path(op.path, path_values)")
    lines.append("    m = op.method")
    lines.append('    if m == "GET":')
    lines.append("        return api.api_get(endpoint, base_url=base_url, params=query)")
    lines.append('    if m == "POST":')
    lines.append("        return api.api_post(endpoint, body, base_url=base_url)")
    lines.append('    if m == "PUT":')
    lines.append("        return api.api_put(endpoint, body, base_url=base_url)")
    lines.append('    if m == "DELETE":')
    lines.append("        return api.api_delete(endpoint, base_url=base_url)")
    lines.append('    if m == "PATCH":')
    lines.append("        return api.api_request('PATCH', endpoint, base_url=base_url, json_data=body, params=query)")
    lines.append('    raise ValueError(f"Unsupported method {m}")')
    lines.append("")
    lines.append("")
    lines.append("def tags() -> list[str]:")
    lines.append("    return sorted({op.tag for op in OPERATIONS.values()})")
    lines.append("")
    lines.append("")
    lines.append("def ops_by_tag(tag: str) -> list[Operation]:")
    lines.append("    return sorted([o for o in OPERATIONS.values() if o.tag == tag], key=lambda o: o.cli_name)")
    return "\n".join(lines)


def _gen_cli(ops: list[dict]) -> str:
    tags = sorted({op["tag"] for op in ops})
    lines = [
        '"""AUTO-GENERATED OpenAPI CLI groups — do not edit."""',
        "from __future__ import annotations",
        "",
        "import json",
        "from typing import Any",
        "",
        "import click",
        "",
        "from cli_fpp.core import confirm as confirm_mod",
        "from cli_fpp.core.openapi_registry import OPERATIONS, execute, ops_by_tag, tags",
        "",
        "",
        "def _output(data: Any, as_json: bool) -> None:",
        "    from cli_fpp.cli import output",
        "",
        "    output(data, as_json)",
        "",
        "",
        "def _conn(ctx: click.Context) -> str:",
        "    return ctx.obj['base_url']",
        "",
        "",
        "def _json(ctx: click.Context) -> bool:",
        "    return ctx.obj.get('as_json', False)",
        "",
        "",
        "def _maybe_confirm(ctx: click.Context, op, action: str) -> bool:",
        "    if not op.mutating:",
        "        return True",
        "    if confirm_mod.is_dry_run(ctx.obj):",
        "        _output(confirm_mod.dry_run_result(action, {'op': op.id}), _json(ctx))",
        "        return False",
        "    if not confirm_mod.require_confirm(ctx.obj, f'{op.method} {op.path}?', as_json=_json(ctx)):",
        "        _output({'cancelled': True, 'action': action, 'op': op.id}, _json(ctx))",
        "        return False",
        "    return True",
        "",
        "",
        "def _make_handler(op_id: str):",
        "    op = OPERATIONS[op_id]",
        "",
        "    def callback(ctx, **kwargs):",
        "        body_raw = kwargs.pop('body', None)",
        "        body = None",
        "        if body_raw:",
        "            body = json.loads(body_raw)",
        "        path_values = {}",
        "        query = {}",
        "        for k, v in list(kwargs.items()):",
        "            if v is None:",
        "                kwargs.pop(k)",
        "        for k, v in kwargs.items():",
        "            if k in op.path_params:",
        "                path_values[k] = str(v)",
        "            elif k in op.query_params:",
        "                query[k] = v",
        "        if not _maybe_confirm(ctx, op, f'api.{op.tag}.{op.cli_name}'):",
        "            return",
        "        result = execute(",
        "            op_id,",
        "            path_values=path_values,",
        "            query=query or None,",
        "            body=body,",
        "            base_url=_conn(ctx),",
        "        )",
        "        _output(result, _json(ctx))",
        "",
        "    params = []",
        "    for pname in op.path_params:",
        "        if pname == '_wildcard':",
        "            params.append(click.Argument(['wildcard'], required=True))",
        "        elif pname == '_tail':",
        "            params.append(click.Argument(['tail'], required=True))",
        "        else:",
        "            params.append(click.Argument([pname], required=True))",
        "    for qname in op.query_params:",
        "        params.append(click.Option([f'--{qname.replace(chr(95), chr(45))}'], required=False))",
        "    if op.method in ('POST', 'PUT', 'PATCH'):",
        "        params.append(click.Option(['--body'], required=False, help='JSON request body'))",
        "    params.append(click.pass_context)",
        "    callback.__doc__ = op.summary",
        "    return click.command(op.cli_name, params=params)(callback)",
        "",
        "",
        "@click.group('api')",
        "def api_group():",
        '    """Full FPP REST API (253 ops from OpenAPI). Use: api <tag> <command>."""',
        "",
        "",
        "@api_group.command('list')",
        "@click.option('--tag', default=None, help='Filter by OpenAPI tag')",
        "@click.pass_context",
        "def api_list(ctx, tag):",
        '    """List wrapped API operations."""',
        "    items = []",
        "    for op in OPERATIONS.values():",
        "        if tag and op.tag != tag:",
        "            continue",
        "        items.append({'tag': op.tag, 'command': op.cli_name, 'method': op.method, 'path': op.path, 'id': op.id})",
        "    _output(sorted(items, key=lambda x: (x['tag'], x['command'])), _json(ctx))",
        "",
        "",
        "@api_group.command('call')",
        "@click.argument('op_id')",
        "@click.option('--path', 'path_json', default=None, help='JSON object of path params')",
        "@click.option('--query', 'query_json', default=None, help='JSON object of query params')",
        "@click.option('--body', 'body_json', default=None, help='JSON request body')",
        "@click.pass_context",
        "def api_call(ctx, op_id, path_json, query_json, body_json):",
        '    """Call any operation by id (from api list)."""',
        "    if op_id not in OPERATIONS:",
        "        raise click.ClickException(f'Unknown op_id: {op_id}')",
        "    op = OPERATIONS[op_id]",
        "    path_values = json.loads(path_json) if path_json else {}",
        "    query = json.loads(query_json) if query_json else None",
        "    body = json.loads(body_json) if body_json else None",
        "    if not _maybe_confirm(ctx, op, f'api.call.{op_id}'):",
        "        return",
        "    _output(execute(op_id, path_values=path_values, query=query, body=body, base_url=_conn(ctx)), _json(ctx))",
        "",
    ]
    for tag in tags:
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", tag)
        lines.append("")
        lines.append(f"@api_group.group('{tag}')")
        lines.append(f"def api_tag_{safe}():")
        lines.append(f'    """OpenAPI tag: {tag}."""')
        lines.append("")
        tag_ops = [op for op in ops if op["tag"] == tag]
        for op in tag_ops:
            lines.append(f"api_tag_{safe}.add_command(_make_handler('{op['id']}'))")
    lines.append("")
    lines.append("")
    lines.append("def register_openapi(cli) -> None:")
    lines.append("    cli.add_command(api_group)")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    spec = json.loads(OPENAPI.read_text(encoding="utf-8"))
    ops = _parse_operations(spec)
    OUT_REGISTRY.write_text(_gen_registry(ops), encoding="utf-8")
    OUT_CLI.write_text(_gen_cli(ops), encoding="utf-8")
    print(f"operations: {len(ops)}")
    print(f"wrote {OUT_REGISTRY}")
    print(f"wrote {OUT_CLI}")


if __name__ == "__main__":
    main()
