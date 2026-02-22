#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CRATE_DIR="$ROOT_DIR/normcore-rs"
TOKEN_FILE="${TOKEN_FILE:-$ROOT_DIR/secrets/crates-io-token}"

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

BRANCH="$(git -C "$ROOT_DIR" branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  echo "ERROR: publish_crates_io.sh must run from main branch (current: $BRANCH)" >&2
  exit 2
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

cd "$CRATE_DIR"
log "Publishing to crates.io"
CARGO_REGISTRY_TOKEN="$TOKEN" cargo publish --manifest-path Cargo.toml
log "Done"
