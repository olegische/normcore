#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTEXT_DIR="$ROOT_DIR/context"
mkdir -p "$CONTEXT_DIR"

MODEL="${MODEL:-gpt-5.2-codex}"
REASONING_EFFORT="${REASONING_EFFORT:-medium}"
PROFILE="${PROFILE:-}"
EVALUATOR_LOG_LEVEL="${EVALUATOR_LOG_LEVEL:-DEBUG}"

RUN_TS="$(date -u +"%Y-%m-%dT%H-%M-%SZ")"
RUN_ID="pypi-smoke-${RUN_TS}"

ROLLOUT_JSONL="$CONTEXT_DIR/${RUN_ID}.jsonl"
ROLLOUT_STDERR="$CONTEXT_DIR/${RUN_ID}.stderr.log"
CONVERSATION_JSON="$CONTEXT_DIR/${RUN_ID}.conversation.json"
JUDGMENT_JSON="$CONTEXT_DIR/${RUN_ID}.judgment.json"

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex command not found in PATH." >&2
  exit 127
fi

if [[ ! -x "$ROOT_DIR/scripts/evaluate_history.sh" ]]; then
  echo "ERROR: missing executable script: $ROOT_DIR/scripts/evaluate_history.sh" >&2
  exit 2
fi

if [[ ! -f "$ROOT_DIR/scripts/codex_exec_events_to_conversation.py" ]]; then
  echo "ERROR: missing converter script: $ROOT_DIR/scripts/codex_exec_events_to_conversation.py" >&2
  exit 2
fi

PROMPT="$(cat <<'EOF'
You are a focused release-readiness reviewer for a Python package.

Goal:
Decide if this package is ready for PyPI based on its public contract and packaging config.

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
  - pyproject.toml
  - src/normcore/__init__.py
  - src/normcore/evaluator.py
  - src/normcore/cli.py
  - README.md
  - tests/models/test_normcore_public_api.py
- Only inspect extra files if strictly needed to confirm a blocker.

Required checks:
1) pyproject.toml packaging/metadata sanity for PyPI.
2) Public API contract consistency:
   - Python API: normcore.evaluate
   - CLI contract: normcore evaluate
   - docs vs implementation mismatch.
3) Minimal release risk callout (only critical items).

Output style:
- Use plain natural language only (no rigid template, no enum labels like READY/NOT_READY).
- Write 4-8 concise sentences total.
- The FIRST sentence must be your publish recommendation (any wording is allowed).
- Put justification only AFTER that first recommendation sentence.
- Include concrete file references when claiming a blocker.
EOF
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
.venv/bin/python "$ROOT_DIR/scripts/codex_exec_events_to_conversation.py" \
  "$ROLLOUT_JSONL" \
  -o "$CONVERSATION_JSON"

log "Evaluating converted conversation with NormCore"
/bin/bash "$ROOT_DIR/scripts/evaluate_history.sh" \
  "$CONVERSATION_JSON" \
  --log-level "$EVALUATOR_LOG_LEVEL" \
  -o "$JUDGMENT_JSON"

log "Done"
echo "Artifacts:"
echo "  rollout_jsonl: $ROLLOUT_JSONL"
echo "  rollout_stderr: $ROLLOUT_STDERR"
echo "  conversation_json: $CONVERSATION_JSON"
echo "  judgment_json: $JUDGMENT_JSON"

if command -v jq >/dev/null 2>&1; then
  echo
  echo "Judgment summary:"
  jq '{status, licensed, can_retry, num_statements, num_acceptable, grounds_accepted, grounds_cited, violated_axioms}' "$JUDGMENT_JSON"
fi
