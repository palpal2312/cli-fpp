#!/usr/bin/env bash
set -euo pipefail

PLAYLIST_NAME="${1:-Holiday}"
shift || true
if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=(shop-a shop-b)
fi

for TARGET in "${TARGETS[@]}"; do
  echo "== Target: $TARGET =="
  cli-fpp --json -t "$TARGET" ping
  cli-fpp --json -t "$TARGET" player status
  cli-fpp --json --dry-run -t "$TARGET" playlist play "$PLAYLIST_NAME" --repeat
  cli-fpp --json --yes -t "$TARGET" playlist play "$PLAYLIST_NAME" --repeat
  cli-fpp --json -t "$TARGET" player current
done
