#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTEXT_DIR="$ROOT_DIR/context"
mkdir -p "$CONTEXT_DIR"

MODEL="${MODEL:-gpt-5.2-codex}"
REASONING_EFFORT="${REASONING_EFFORT:-medium}"
PROFILE="${PROFILE:-}"
EVALUATOR_LOG_LEVEL="${EVALUATOR_LOG_LEVEL:-DEBUG}"
NORMCORE_PYPI_SPEC="${NORMCORE_PYPI_SPEC:-normcore}"
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN_DEFAULT="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN_DEFAULT="$(command -v python3)"
fi
PYTHON_BIN="${PYTHON_BIN:-$PYTHON_BIN_DEFAULT}"

RUN_TS="$(date -u +"%Y-%m-%dT%H-%M-%SZ")"
RUN_ID="pypi-smoke-${RUN_TS}"

ROLLOUT_JSONL="$CONTEXT_DIR/${RUN_ID}.jsonl"
ROLLOUT_STDERR="$CONTEXT_DIR/${RUN_ID}.stderr.log"
CONVERSATION_JSON="$CONTEXT_DIR/${RUN_ID}.conversation.json"
JUDGMENT_JSON="$CONTEXT_DIR/${RUN_ID}.judgment.json"

VENV_DIR="$(mktemp -d /tmp/normcore-pypi-smoke.XXXXXX)"
cleanup() {
  rm -rf "$VENV_DIR"
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

PROMPT="$(cat <<'PROMPT_EOF'
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
  - normcore-py/src/normcore/__init__.py
  - normcore-py/src/normcore/evaluator.py
  - normcore-py/src/normcore/cli.py
  - README.md
  - normcore-py/tests/models/test_normcore_public_api.py
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
python3 "$ROOT_DIR/scripts/codex_exec_events_to_conversation.py" \
  "$ROLLOUT_JSONL" \
  -o "$CONVERSATION_JSON"

log "Creating temporary virtualenv: $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null

log "Installing from PyPI: $NORMCORE_PYPI_SPEC"
"$VENV_DIR/bin/pip" install "$NORMCORE_PYPI_SPEC"

log "Evaluating converted conversation with PyPI NormCore"
"$VENV_DIR/bin/python" - <<'PY' "$CONVERSATION_JSON" "$JUDGMENT_JSON" "$EVALUATOR_LOG_LEVEL"
import json
import sys
from pathlib import Path

conversation_path = Path(sys.argv[1])
judgment_path = Path(sys.argv[2])
log_level = sys.argv[3] or None

from normcore import evaluate
from normcore.logging import configure_logging

configure_logging(level=log_level)
conversation = json.loads(conversation_path.read_text(encoding="utf-8"))
judgment = evaluate(conversation=conversation)
rendered = json.dumps(judgment.model_dump(mode="json"), ensure_ascii=False, indent=2)
judgment_path.write_text(rendered + "\n", encoding="utf-8")
print(f"Wrote judgment to {judgment_path}", file=sys.stderr)
PY

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
