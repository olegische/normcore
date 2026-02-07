#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEXT="${*:-The deployment is blocked, so we should fix it first.}"

cd "$ROOT_DIR"
UV_CACHE_DIR=.uv-cache uv run normcore evaluate --text "$TEXT"
