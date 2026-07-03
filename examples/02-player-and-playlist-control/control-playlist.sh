#!/usr/bin/env bash
set -euo pipefail

PLAYLIST_NAME="${1:-Holiday}"

cli-fpp --json player status
cli-fpp --json player current
cli-fpp --json playlist list --playable

cli-fpp --json --dry-run playlist play "$PLAYLIST_NAME" --repeat
cli-fpp --json --yes playlist play "$PLAYLIST_NAME" --repeat

cli-fpp --json playlist next
cli-fpp --json --yes playlist stop --now
