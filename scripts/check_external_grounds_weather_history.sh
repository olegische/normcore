#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CONVERSATION_JSON='[
  {
    "role": "system",
    "content": "RAG_CONTEXT file_weather_archive_2025: On 2025-02-07 in New York, condition=snow, temperature_c=-1, source=weather_archive_file."
  },
  {
    "role": "user",
    "content": "What is the weather in New York today, and how does it compare to last year?"
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
    "content": "It is warmer and rainy in New York today compared to one year ago, so you should carry an umbrella [@callWeatherNYC] [@file_weather_archive_2025]."
  }
]'

GROUNDS_JSON='[
  {
    "type": "file_citation",
    "file_id": "file_weather_archive_2025",
    "filename": "ny_weather_2025.txt",
    "index": 0
  }
]'

cd "$ROOT_DIR"
OUTPUT="$(UV_CACHE_DIR=.uv-cache uv run normcore evaluate \
  --conversation "$CONVERSATION_JSON" \
  --grounds "$GROUNDS_JSON")"

echo "$OUTPUT"

if command -v jq >/dev/null 2>&1; then
  if echo "$OUTPUT" | jq -e '
    .statement_evaluations[0].grounding_trace as $g
    | ($g | length >= 2)
      and
      (($g | map(.semantic_id) | index("file_weather_archive_2025")) != null)
  ' >/dev/null; then
    echo
    echo "PASS: grounding_trace includes weather ground + external file-based historical ground."
    exit 0
  fi
  echo
  echo "FAIL: expected weather + external historical ground in grounding_trace." >&2
  exit 1
fi

echo
echo "NOTE: jq not installed, skipped automatic PASS/FAIL assertion."
