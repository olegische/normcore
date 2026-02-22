#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT_DIR="$ROOT_DIR/context"
mkdir -p "$CONTEXT_DIR"

if [[ -x "$ROOT_DIR/normcore-py/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/normcore-py/.venv/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

MODEL="${MODEL:-gpt-5.2-codex}"
REASONING_EFFORT="${REASONING_EFFORT:-medium}"
PROFILE="${PROFILE:-}"
CRATE_DIR="$ROOT_DIR/normcore-rs"
RUST_SMOKE_SOURCE="${RUST_SMOKE_SOURCE:-published}"

CRATE_NAME="$(
  sed -n 's/^name = "\(.*\)"/\1/p' "$CRATE_DIR/Cargo.toml" | head -n 1
)"
CRATE_VERSION="$(
  sed -n 's/^version = "\(.*\)"/\1/p' "$CRATE_DIR/Cargo.toml" | head -n 1
)"
if [[ -z "$CRATE_NAME" || -z "$CRATE_VERSION" ]]; then
  echo "ERROR: failed to read crate name/version from $CRATE_DIR/Cargo.toml" >&2
  exit 2
fi

RUN_TS="$(date -u +"%Y-%m-%dT%H-%M-%SZ")"
RUN_ID="rust-crates-smoke-${RUN_TS}"

ROLLOUT_JSONL="$CONTEXT_DIR/${RUN_ID}.jsonl"
ROLLOUT_STDERR="$CONTEXT_DIR/${RUN_ID}.stderr.log"
CONVERSATION_JSON="$CONTEXT_DIR/${RUN_ID}.conversation.json"
JUDGMENT_JSON="$CONTEXT_DIR/${RUN_ID}.judgment.json"

TMP_DIR="$(mktemp -d /tmp/normcore-rs-codex-smoke.XXXXXX)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex command not found in PATH." >&2
  exit 127
fi

if [[ ! -f "$ROOT_DIR/scripts/codex_exec_events_to_conversation.py" ]]; then
  echo "ERROR: missing converter script: $ROOT_DIR/scripts/codex_exec_events_to_conversation.py" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required for smoke validation." >&2
  exit 127
fi

PROMPT="$(cat <<'PROMPT_EOF'
You are a focused release-readiness reviewer for a Rust crate.

Goal:
Decide if this crate is ready for crates.io based on public contract and package config.

Constraints:
- Respond in English.
- Do not modify files.
- Keep the review focused and concise.
- If you cite file-based evidence, append citation keys in `[@key]` format.
- For file citations, use:
  `[@file_<hash12>]`, where `hash12` is the first 12 hex chars of
  `sha256(normalized_repo_relative_file_path)`.
- Normalize file paths before hashing:
  remove leading `./`, use `/` separators, use repo-relative path.
- Compute hashes via tools; do not invent citation keys.
- Inspect primarily these files:
  - normcore-rs/Cargo.toml
  - normcore-rs/src/lib.rs
  - normcore-rs/src/main.rs
  - normcore-rs/README.md
  - README.md
  - normcore-rs/tests/evaluate_scenarios.rs
- Only inspect extra files if strictly needed to confirm a blocker.

Required checks:
1) Cargo.toml packaging/metadata sanity for crates.io.
2) Public API contract consistency:
   - Rust library API exports
   - CLI contract: `normcore evaluate`
   - docs vs implementation mismatch.
3) Minimal release risk callout (only critical items).

Output style:
- Use plain natural language only (no rigid template, no enum labels like READY/NOT_READY).
- Write 4-8 concise sentences total.
- The FIRST sentence must be your publish recommendation (any wording is allowed).
- Put justification only AFTER that first recommendation sentence.
- Include concrete file references when claiming a blocker.
PROMPT_EOF
)"

CODEX_ARGS=(
  exec
  --model "$MODEL"
  --cd "$ROOT_DIR"
  --skip-git-repo-check
  --json
  -c "effort=\"$REASONING_EFFORT\""
)

if [[ -n "$PROFILE" ]]; then
  CODEX_ARGS+=(--profile "$PROFILE")
fi

log "Launching codex exec (model=$MODEL, effort=$REASONING_EFFORT)"
log "Writing rollout to: $ROLLOUT_JSONL"
log "Writing codex stderr to: $ROLLOUT_STDERR"

echo "$PROMPT" | codex "${CODEX_ARGS[@]}" 2>"$ROLLOUT_STDERR" | tee "$ROLLOUT_JSONL"
CODEX_EXIT=${PIPESTATUS[1]}

if [[ $CODEX_EXIT -ne 0 ]]; then
  echo "ERROR: codex exec failed with exit code $CODEX_EXIT" >&2
  echo "See logs:" >&2
  echo "  rollout: $ROLLOUT_JSONL" >&2
  echo "  stderr : $ROLLOUT_STDERR" >&2
  exit $CODEX_EXIT
fi

log "Converting rollout JSONL to conversation JSON"
"$PYTHON_BIN" "$ROOT_DIR/scripts/codex_exec_events_to_conversation.py" \
  "$ROLLOUT_JSONL" \
  -o "$CONVERSATION_JSON"

CONVERSATION_PAYLOAD="$(cat "$CONVERSATION_JSON")"

case "$RUST_SMOKE_SOURCE" in
  published)
    INSTALL_ROOT="$TMP_DIR/install"
    log "Installing published crate from crates.io: $CRATE_NAME@$CRATE_VERSION"
    cargo install --locked --root "$INSTALL_ROOT" --version "$CRATE_VERSION" "$CRATE_NAME"

    BIN_PATH="$INSTALL_ROOT/bin/$CRATE_NAME"
    if [[ ! -x "$BIN_PATH" ]]; then
      echo "ERROR: installed binary not found: $BIN_PATH" >&2
      exit 2
    fi

    log "Evaluating converted conversation with published crates.io binary"
    "$BIN_PATH" evaluate --conversation "$CONVERSATION_PAYLOAD" > "$JUDGMENT_JSON"
    ;;
  artifact)
    log "Packaging crate artifact (offline): $CRATE_NAME@$CRATE_VERSION"
    cargo package --offline --manifest-path "$CRATE_DIR/Cargo.toml"

    CRATE_PATH="$CRATE_DIR/target/package/${CRATE_NAME}-${CRATE_VERSION}.crate"
    if [[ ! -f "$CRATE_PATH" ]]; then
      echo "ERROR: packaged crate not found: $CRATE_PATH" >&2
      exit 2
    fi

    PKG_TMP="$TMP_DIR/package"
    mkdir -p "$PKG_TMP"
    tar -xzf "$CRATE_PATH" -C "$PKG_TMP"
    PKG_DIR="$PKG_TMP/${CRATE_NAME}-${CRATE_VERSION}"

    if [[ ! -f "$PKG_DIR/Cargo.toml" ]]; then
      echo "ERROR: unpacked Cargo.toml not found: $PKG_DIR/Cargo.toml" >&2
      exit 2
    fi

    log "Evaluating converted conversation with packaged crate artifact"
    cargo run --offline --manifest-path "$PKG_DIR/Cargo.toml" -- \
      evaluate --conversation "$CONVERSATION_PAYLOAD" > "$JUDGMENT_JSON"
    ;;
  *)
    echo "ERROR: unknown RUST_SMOKE_SOURCE='$RUST_SMOKE_SOURCE' (expected 'published' or 'artifact')" >&2
    exit 2
    ;;
esac

log "Done"
echo "Artifacts:"
echo "  rollout_jsonl: $ROLLOUT_JSONL"
echo "  rollout_stderr: $ROLLOUT_STDERR"
echo "  conversation_json: $CONVERSATION_JSON"
echo "  judgment_json: $JUDGMENT_JSON"

echo
echo "Judgment summary:"
jq '{status, licensed, can_retry, num_statements, num_acceptable, grounds_accepted, grounds_cited, violated_axioms}' "$JUDGMENT_JSON"
