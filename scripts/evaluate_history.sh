#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  scripts/evaluate_history.sh <conversation.json> [--grounds <grounds.json>] [--agent-output <text>] [--log-level <LEVEL>] [-o|--output <judgment.json>]

Examples:
  scripts/evaluate_history.sh context/rollout.conversation.json
  scripts/evaluate_history.sh context/rollout.conversation.json --grounds context/grounds.json -o context/judgment.json
EOF
}

CONVERSATION_PATH=""
GROUNDS_PATH=""
OUTPUT_PATH=""
AGENT_OUTPUT_VAL=""
AGENT_OUTPUT_SET="0"
LOG_LEVEL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --grounds)
      [[ $# -ge 2 ]] || { echo "Missing value for --grounds" >&2; exit 2; }
      GROUNDS_PATH="$2"
      shift 2
      ;;
    --agent-output)
      [[ $# -ge 2 ]] || { echo "Missing value for --agent-output" >&2; exit 2; }
      AGENT_OUTPUT_VAL="$2"
      AGENT_OUTPUT_SET="1"
      shift 2
      ;;
    --log-level)
      [[ $# -ge 2 ]] || { echo "Missing value for --log-level" >&2; exit 2; }
      LOG_LEVEL="$2"
      shift 2
      ;;
    -o|--output)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      OUTPUT_PATH="$2"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      if [[ -z "$CONVERSATION_PATH" ]]; then
        CONVERSATION_PATH="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage
        exit 2
      fi
      ;;
  esac
done

if [[ -z "$CONVERSATION_PATH" ]]; then
  usage
  exit 2
fi

cd "$ROOT_DIR"

CONVERSATION_PATH="$CONVERSATION_PATH" \
GROUNDS_PATH="$GROUNDS_PATH" \
OUTPUT_PATH="$OUTPUT_PATH" \
AGENT_OUTPUT_VAL="$AGENT_OUTPUT_VAL" \
AGENT_OUTPUT_SET="$AGENT_OUTPUT_SET" \
LOG_LEVEL="$LOG_LEVEL" \
.venv/bin/python - <<'PY'
import json
import os
import sys
from pathlib import Path


def load_json_array(path_str: str, label: str):
    path = Path(path_str)
    if not path.exists():
        raise SystemExit(f"{label} file not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {label} file {path}: {exc}") from exc
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a JSON array: {path}")
    return value


conversation = load_json_array(os.environ["CONVERSATION_PATH"], "conversation")
grounds_path = os.environ.get("GROUNDS_PATH", "").strip()
grounds = load_json_array(grounds_path, "grounds") if grounds_path else None

try:
    from normcore import evaluate
    from normcore.logging import configure_logging
except ModuleNotFoundError:
    src_dir = Path.cwd() / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from normcore import evaluate
    from normcore.logging import configure_logging

log_level = os.environ.get("LOG_LEVEL", "").strip() or None
configure_logging(level=log_level)

kwargs = {"conversation": conversation, "grounds": grounds}
if os.environ.get("AGENT_OUTPUT_SET") == "1":
    kwargs["agent_output"] = os.environ.get("AGENT_OUTPUT_VAL", "")

judgment = evaluate(**kwargs)
rendered = json.dumps(judgment.model_dump(mode="json"), ensure_ascii=False, indent=2)

output_path = os.environ.get("OUTPUT_PATH", "").strip()
if output_path:
    Path(output_path).write_text(rendered + "\n", encoding="utf-8")
    print(f"Wrote judgment to {output_path}", file=sys.stderr)
else:
    print(rendered)
PY
