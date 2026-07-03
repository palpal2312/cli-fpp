#!/usr/bin/env bash
set -euo pipefail

MEDIA_SOURCE="${1:?Usage: ./upload-media-workflow.sh <file-or-url>}"

cli-fpp --json media propose "$MEDIA_SOURCE"
cli-fpp --json --dry-run media upload "$MEDIA_SOURCE"
cli-fpp --json --yes media upload "$MEDIA_SOURCE"
cli-fpp --json media list
