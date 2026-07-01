---
name: cli-fpp
description: Command-line client for Falcon Player (FPP). Control playlists, commands, and fppd via REST API.
---

# cli-fpp

Remote CLI for [Falcon Player](https://github.com/FalconChristmas/fpp). Wraps `/api/*` — no FPP binary on the client.

## Setup

```bash
pip install cli-fpp
export FPP_BASE_URL=http://fpp.local
```

## Commands

`ping`, `system status`, `playlist play NAME`, `command run "Volume Set" 80`, `schedule reload`

Use `--json` for agent workflows.

## Examples

```bash
cli-fpp --url http://fpp.local --json system status
cli-fpp playlist play "Show" --repeat
```
