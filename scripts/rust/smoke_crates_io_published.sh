#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CRATE_DIR="$ROOT_DIR/normcore-rs"

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

CRATE_NAME="$(
  sed -n 's/^name = "\(.*\)"/\1/p' "$CRATE_DIR/Cargo.toml" | head -n 1
)"
CRATE_VERSION="$(
  sed -n 's/^version = "\(.*\)"/\1/p' "$CRATE_DIR/Cargo.toml" | head -n 1
)"

if [[ -z "$CRATE_NAME" || -z "$CRATE_VERSION" ]]; then
  echo "ERROR: failed to read crate name/version from Cargo.toml" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required for smoke validation." >&2
  exit 127
fi

TMP_DIR="$(mktemp -d /tmp/normcore-rs-crates-smoke.XXXXXX)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

INSTALL_ROOT="$TMP_DIR/install"

log "Installing published crate from crates.io: $CRATE_NAME@$CRATE_VERSION"
cargo install --locked --root "$INSTALL_ROOT" --version "$CRATE_VERSION" "$CRATE_NAME"

BIN_PATH="$INSTALL_ROOT/bin/$CRATE_NAME"
if [[ ! -x "$BIN_PATH" ]]; then
  echo "ERROR: installed binary not found: $BIN_PATH" >&2
  exit 2
fi

OUT_JSON="$TMP_DIR/judgment.json"
log "Running CLI smoke from published binary"
"$BIN_PATH" evaluate --agent-output "The deployment is blocked, so we should wait." > "$OUT_JSON"

STATUS="$(jq -r '.status' "$OUT_JSON")"
LICENSED="$(jq -r '.licensed' "$OUT_JSON")"
if [[ "$STATUS" == "null" || "$LICENSED" == "null" ]]; then
  echo "ERROR: expected status/licensed in smoke output" >&2
  cat "$OUT_JSON" >&2
  exit 2
fi

log "Published smoke output status=$STATUS licensed=$LICENSED"
cat "$OUT_JSON"
