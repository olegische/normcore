#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEXT="${*:-The deployment is blocked, so we should fix it first.}"

cd "$ROOT_DIR"
cargo run --quiet --manifest-path normcore-rs/Cargo.toml -- evaluate --agent-output "$TEXT"
