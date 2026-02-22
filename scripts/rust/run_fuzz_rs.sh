#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-}"
RUNS="${2:-5000}"

if [[ -z "$TARGET" ]]; then
  cat <<'USAGE' >&2
Usage:
  scripts/rust/run_fuzz_rs.sh <target> [runs]

Targets:
  fuzz_parse_json
  fuzz_parse_conversation
  fuzz_extract_citation_keys
USAGE
  exit 2
fi

if ! command -v cargo-fuzz >/dev/null 2>&1; then
  echo "cargo-fuzz is not installed. Install it with: cargo install cargo-fuzz" >&2
  exit 2
fi

cd "$ROOT_DIR/normcore-rs"
cargo fuzz run "$TARGET" -- -runs="$RUNS"
