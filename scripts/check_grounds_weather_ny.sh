#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CONVERSATION_JSON='[
  {
    "role": "user",
    "content": "What is the weather in New York and what should I do?"
  },
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "callWeatherNYC",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\":\"New York\",\"units\":\"metric\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "callWeatherNYC",
    "content": "{\"weather_id\":\"nyc_2026-02-07\",\"city\":\"New York\",\"condition\":\"rain\",\"temperature_c\":4}"
  },
  {
    "role": "assistant",
    "content": "You should carry an umbrella in New York today [@callWeatherNYC]."
  }
]'

cd "$ROOT_DIR"
OUTPUT="$(UV_CACHE_DIR=.uv-cache uv run normcore evaluate --conversation "$CONVERSATION_JSON")"

echo "$OUTPUT"

if command -v jq >/dev/null 2>&1; then
  if echo "$OUTPUT" | jq -e '.statement_evaluations[0].grounding_trace | length > 0' >/dev/null; then
    echo
    echo "PASS: grounding_trace contains grounds from tool conversation."
    exit 0
  fi
  echo
  echo "FAIL: grounding_trace is empty." >&2
  exit 1
fi

echo
echo "NOTE: jq not installed, skipped automatic PASS/FAIL assertion."
