#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CRATE_DIR="$ROOT_DIR/normcore-rs"

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

cd "$CRATE_DIR"

CRATE_VERSION="$(
  sed -n 's/^version = "\(.*\)"/\1/p' Cargo.toml | head -n 1
)"
if [[ -z "$CRATE_VERSION" ]]; then
  echo "ERROR: failed to read crate version from Cargo.toml" >&2
  exit 2
fi

log "Packaging crate (offline)"
cargo package --offline --manifest-path Cargo.toml

CRATE_PATH="$CRATE_DIR/target/package/normcore-${CRATE_VERSION}.crate"
if [[ ! -f "$CRATE_PATH" ]]; then
  echo "ERROR: packaged crate not found: $CRATE_PATH" >&2
  exit 2
fi

TMP_DIR="$(mktemp -d /tmp/normcore-rs-artifact.XXXXXX)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

log "Unpacking artifact: $CRATE_PATH"
tar -xzf "$CRATE_PATH" -C "$TMP_DIR"
PKG_DIR="$TMP_DIR/normcore-${CRATE_VERSION}"

if [[ ! -f "$PKG_DIR/Cargo.toml" ]]; then
  echo "ERROR: unpacked Cargo.toml not found: $PKG_DIR/Cargo.toml" >&2
  exit 2
fi

OUT_JSON="$TMP_DIR/judgment.json"
log "Running CLI smoke from packaged artifact"
cargo run --offline --manifest-path "$PKG_DIR/Cargo.toml" -- \
  evaluate --agent-output "The deployment is blocked, so we should wait." >"$OUT_JSON"

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required for smoke validation." >&2
  exit 127
fi

STATUS="$(jq -r '.status' "$OUT_JSON")"
LICENSED="$(jq -r '.licensed' "$OUT_JSON")"
if [[ "$STATUS" == "null" || "$LICENSED" == "null" ]]; then
  echo "ERROR: expected status/licensed in smoke output" >&2
  cat "$OUT_JSON" >&2
  exit 2
fi

log "Smoke output status=$STATUS licensed=$LICENSED"
cat "$OUT_JSON"
