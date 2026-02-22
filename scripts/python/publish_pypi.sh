#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG_DIR="$ROOT_DIR/normcore-py"
TOKEN_FILE="${TOKEN_FILE:-$ROOT_DIR/secrets/pypi-api-token}"
REPOSITORY_URL="${REPOSITORY_URL:-https://upload.pypi.org/legacy/}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.uv-cache}"

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  echo "ERROR: publish_pypi.sh must run from main branch (current: $BRANCH)" >&2
  exit 2
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required but not found in PATH." >&2
  exit 127
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "ERROR: token file not found: $TOKEN_FILE" >&2
  exit 2
fi

TOKEN="$(head -n 1 "$TOKEN_FILE" | tr -d '\r\n')"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: first line in token file is empty: $TOKEN_FILE" >&2
  exit 2
fi

cd "$PKG_DIR"
rm -rf dist

log "Building wheel and sdist"
uv run --with build -- python -m build --sdist --wheel

log "Checking dist metadata"
uv run --with twine -- twine check dist/*

log "Uploading to PyPI"
TWINE_USERNAME="__token__" \
TWINE_PASSWORD="$TOKEN" \
uv run --with twine -- twine upload --non-interactive --repository-url "$REPOSITORY_URL" dist/*

log "Done"
