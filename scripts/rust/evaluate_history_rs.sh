#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage:
  scripts/rust/evaluate_history_rs.sh <conversation.json> [--grounds <grounds.json>] [--agent-output <text>] [--log-level <LEVEL>] [-o|--output <judgment.json>]
USAGE
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

[[ -f "$CONVERSATION_PATH" ]] || { echo "conversation file not found: $CONVERSATION_PATH" >&2; exit 2; }
CONVERSATION_JSON="$(cat "$CONVERSATION_PATH")"

GROUNDS_ARGS=()
if [[ -n "$GROUNDS_PATH" ]]; then
  [[ -f "$GROUNDS_PATH" ]] || { echo "grounds file not found: $GROUNDS_PATH" >&2; exit 2; }
  GROUNDS_JSON="$(cat "$GROUNDS_PATH")"
  GROUNDS_ARGS+=(--grounds "$GROUNDS_JSON")
fi

AGENT_ARGS=()
if [[ "$AGENT_OUTPUT_SET" == "1" ]]; then
  AGENT_ARGS+=(--agent-output "$AGENT_OUTPUT_VAL")
fi

LOG_ARGS=()
if [[ -n "$LOG_LEVEL" ]]; then
  LOG_ARGS+=(--log-level "$LOG_LEVEL")
fi

cd "$ROOT_DIR"
OUTPUT="$(cargo run --quiet --manifest-path src/normcore-rs/Cargo.toml -- evaluate \
  --conversation "$CONVERSATION_JSON" \
  "${GROUNDS_ARGS[@]}" \
  "${AGENT_ARGS[@]}" \
  "${LOG_ARGS[@]}")"

if [[ -n "$OUTPUT_PATH" ]]; then
  printf '%s\n' "$OUTPUT" > "$OUTPUT_PATH"
  echo "Wrote judgment to $OUTPUT_PATH" >&2
else
  echo "$OUTPUT"
fi
