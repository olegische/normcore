#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CRATE_DIR="$ROOT_DIR/normcore-rs"
OUT_BASE="$ROOT_DIR/artifacts/mutation"
STAMP="$(date +"%Y%m%d-%H%M%S")"
OUT_DIR="$OUT_BASE/$STAMP"

has_output_arg() {
  local prev=""
  for arg in "$@"; do
    if [[ "$arg" == "--output" || "$arg" == "-o" ]]; then
      return 0
    fi
    if [[ "$prev" == "--output" || "$prev" == "-o" ]]; then
      return 0
    fi
    prev="$arg"
  done
  return 1
}

has_colors_arg() {
  local prev=""
  for arg in "$@"; do
    if [[ "$arg" == "--colors" ]]; then
      return 0
    fi
    if [[ "$prev" == "--colors" ]]; then
      return 0
    fi
    prev="$arg"
  done
  return 1
}

if command -v cargo-mutants >/dev/null 2>&1; then
  CARGO_MUTANTS_BIN="cargo-mutants"
elif [[ -x "$HOME/.cargo/bin/cargo-mutants" ]]; then
  CARGO_MUTANTS_BIN="$HOME/.cargo/bin/cargo-mutants"
else
  echo "cargo-mutants is not installed. Install it with: cargo install cargo-mutants" >&2
  exit 2
fi

mkdir -p "$OUT_BASE"
cd "$CRATE_DIR"

if has_output_arg "$@"; then
  "$CARGO_MUTANTS_BIN" mutants "$@"
else
  mkdir -p "$OUT_DIR"
  LOG_FILE="$OUT_DIR/run.log"
  EXTRA_ARGS=()
  if ! has_colors_arg "$@"; then
    EXTRA_ARGS+=(--colors always)
  fi
  echo "Mutation report directory: $OUT_DIR"
  "$CARGO_MUTANTS_BIN" mutants -o "$OUT_DIR" "${EXTRA_ARGS[@]}" "$@" 2>&1 | tee "$LOG_FILE"
  echo "Saved mutation log: $LOG_FILE"
  echo "Saved mutation report: $OUT_DIR/mutants.out"
fi
