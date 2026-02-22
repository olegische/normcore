#!/usr/bin/env python3
"""Convert TLC trace output with a `log = <<...>>` state field into replay JSON.

Expected output format:
{
  "steps": [
    {
      "op": "CoreEvaluateSingleStatement",
      "args": { ... replay input ... },
      "expect": {
        "status": "acceptable",
        "licensed": true,
        "can_retry": false,
        "num_statements": 1
      }
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ParseError(RuntimeError):
    pass


@dataclass
class Parser:
    text: str
    i: int = 0

    def parse_value(self) -> Any:
        self._skip_ws()
        if self._peek("<<"):
            return self._parse_seq()
        if self._peek("["):
            return self._parse_record()
        if self._peek('"'):
            return self._parse_string()
        if self._peek_word("TRUE"):
            self.i += 4
            return True
        if self._peek_word("FALSE"):
            self.i += 5
            return False
        if self._peek_number_start():
            return self._parse_number()
        ident = self._parse_identifier()
        if ident is None:
            raise ParseError(f"Unexpected token at offset {self.i}")
        return ident

    def _parse_seq(self) -> list[Any]:
        self._expect("<<")
        out: list[Any] = []
        self._skip_ws()
        if self._peek(">>"):
            self.i += 2
            return out
        while True:
            out.append(self.parse_value())
            self._skip_ws()
            if self._peek(">>"):
                self.i += 2
                break
            self._expect(",")
        return out

    def _parse_record(self) -> dict[str, Any]:
        self._expect("[")
        out: dict[str, Any] = {}
        self._skip_ws()
        if self._peek("]"):
            self.i += 1
            return out
        while True:
            key = self._parse_identifier()
            if key is None:
                raise ParseError(f"Record key expected at offset {self.i}")
            self._skip_ws()
            self._expect("|->")
            value = self.parse_value()
            out[key] = value
            self._skip_ws()
            if self._peek("]"):
                self.i += 1
                break
            self._expect(",")
        return out

    def _parse_string(self) -> str:
        self._expect('"')
        escaped = False
        buf: list[str] = ['"']
        while self.i < len(self.text):
            ch = self.text[self.i]
            self.i += 1
            buf.append(ch)
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                break
        raw = "".join(buf)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid string literal {raw!r}: {exc}") from exc

    def _parse_number(self) -> int | float:
        start = self.i
        if self._peek("-"):
            self.i += 1
        while self.i < len(self.text) and self.text[self.i].isdigit():
            self.i += 1
        if self.i < len(self.text) and self.text[self.i] == ".":
            self.i += 1
            while self.i < len(self.text) and self.text[self.i].isdigit():
                self.i += 1
        number_text = self.text[start:self.i]
        try:
            if "." in number_text:
                return float(number_text)
            return int(number_text)
        except ValueError as exc:
            raise ParseError(f"Invalid number literal: {number_text!r}") from exc

    def _parse_identifier(self) -> str | None:
        self._skip_ws()
        if self.i >= len(self.text):
            return None
        ch = self.text[self.i]
        if not (ch.isalpha() or ch == "_"):
            return None
        start = self.i
        self.i += 1
        while self.i < len(self.text):
            ch = self.text[self.i]
            if ch.isalnum() or ch == "_":
                self.i += 1
            else:
                break
        return self.text[start:self.i]

    def _peek_number_start(self) -> bool:
        self._skip_ws()
        if self.i >= len(self.text):
            return False
        ch = self.text[self.i]
        if ch == "-":
            return self.i + 1 < len(self.text) and self.text[self.i + 1].isdigit()
        return ch.isdigit()

    def _peek_word(self, word: str) -> bool:
        self._skip_ws()
        return self.text.startswith(word, self.i)

    def _peek(self, token: str) -> bool:
        self._skip_ws()
        return self.text.startswith(token, self.i)

    def _expect(self, token: str) -> None:
        self._skip_ws()
        if not self.text.startswith(token, self.i):
            raise ParseError(f"Expected {token!r} at offset {self.i}")
        self.i += len(token)

    def _skip_ws(self) -> None:
        while self.i < len(self.text) and self.text[self.i].isspace():
            self.i += 1


def extract_last_log(text: str) -> list[dict[str, Any]]:
    matches = list(re.finditer(r"\blog\b\s*=", text))
    if not matches:
        raise ParseError("No 'log =' assignment found in TLC output")

    for match in reversed(matches):
        parser = Parser(text[match.end() :])
        try:
            value = parser.parse_value()
        except ParseError:
            continue
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]

    raise ParseError("Failed to parse any log sequence from TLC output")


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.lower()
        if lower in {"true", "yes", "1"}:
            return True
        if lower in {"false", "no", "0"}:
            return False
    return default


def as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def map_core_status(core_status: str) -> str:
    mapping = {
        "ACCEPTABLE": "acceptable",
        "CONDITIONALLY_ACCEPTABLE": "conditionally_acceptable",
        "VIOLATES_NORM": "violates_norm",
        "UNSUPPORTED": "unsupported",
        "ILL_FORMED": "ill_formed",
        "UNDERDETERMINED": "underdetermined",
        "NO_NORMATIVE_CONTENT": "no_normative_content",
        "WELL_FORMED": "underdetermined",
    }
    return mapping.get(core_status, "underdetermined")


def normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return "underdetermined"
    v = value.strip().lower()
    allowed = {
        "acceptable",
        "conditionally_acceptable",
        "violates_norm",
        "unsupported",
        "ill_formed",
        "underdetermined",
        "no_normative_content",
    }
    return v if v in allowed else "underdetermined"


def materialize_args(replay_case: str) -> dict[str, Any]:
    if replay_case == "empty_output":
        return {"agent_output": ""}
    if replay_case == "no_normative":
        return {"agent_output": "Hello! How can I help you today?"}
    if replay_case == "assistant_refusal":
        return {"agent_output": "I cannot determine from current context."}
    if replay_case == "assertive_unlicensed":
        return {"agent_output": "We should deploy now."}
    if replay_case == "conditional_declared":
        return {"agent_output": "If latency matters, choose A."}
    if replay_case == "descriptive_ungrounded":
        return {"agent_output": "The deployment is blocked by migration."}

    return {
        "conversation": [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "callWeatherNYC",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": "{\"city\":\"New York\"}",
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "callWeatherNYC",
                "content": "{\"weather_id\":\"nyc_2026-02-07\"}",
            },
            {
                "role": "assistant",
                "content": "You should carry an umbrella [@callWeatherNYC].",
            },
        ]
    }


def convert_events_to_steps(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for event in events:
        op = str(event.get("op", "Unknown"))
        args_raw = event.get("args", {}) if isinstance(event.get("args"), dict) else {}
        expect_raw = event.get("expect", {}) if isinstance(event.get("expect"), dict) else {}

        replay_case = str(args_raw.get("replayCase", "assertive_unlicensed"))
        args = materialize_args(replay_case)

        explicit_status = expect_raw.get("status")
        core_status = str(expect_raw.get("coreStatus", "UNDERDETERMINED"))
        status = (
            normalize_status(explicit_status)
            if explicit_status is not None
            else map_core_status(core_status)
        )
        expect = {
            "status": status,
            "licensed": as_bool(expect_raw.get("licensed"), False),
            "can_retry": as_bool(
                expect_raw.get("can_retry", expect_raw.get("canRetry")), False
            ),
            "num_statements": as_int(
                expect_raw.get("num_statements", expect_raw.get("numStatements")), 0
            ),
        }

        steps.append({"op": op, "args": args, "expect": expect})
    return steps


def load_input(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def write_output(payload: dict[str, Any], path: str | None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Path to TLC stdout file (default: stdin)")
    parser.add_argument("--output", help="Path to JSON output (default: stdout)")
    args = parser.parse_args()

    try:
        text = load_input(args.input)
        events = extract_last_log(text)
        steps = convert_events_to_steps(events)
        if not steps:
            raise ParseError("Parsed log is empty; no steps to export")
        write_output({"steps": steps}, args.output)
        return 0
    except (OSError, ParseError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
