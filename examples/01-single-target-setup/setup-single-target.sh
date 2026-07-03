#!/usr/bin/env bash
set -euo pipefail

TARGET_NAME="${1:-shop-a}"
FPP_URL="${2:-http://192.168.1.10:81}"
FPP_USER="${3:-admin}"
FPP_PASSWORD="${4:-change-me}"

cli-fpp --json target add "$TARGET_NAME" \
  --fpp-url "$FPP_URL" \
  --fpp-user "$FPP_USER" \
  --fpp-password "$FPP_PASSWORD" \
  --default

cli-fpp --json target use "$TARGET_NAME"
cli-fpp --json ping
cli-fpp --json config show
cli-fpp --json doctor
