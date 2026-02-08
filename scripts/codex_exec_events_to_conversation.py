#!/usr/bin/env python3
"""
Convert `codex exec --json` event stream into NormCore conversation JSON.

Input format (live/non-session):
- {"type":"item.started","item":{"type":"command_execution", ...}}
- {"type":"item.completed","item":{"type":"command_execution"|"agent_message"|"reasoning", ...}}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {idx}: {exc}") from exc
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _serialize_any(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False)


_FILE_TOKEN_RE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+\.[A-Za-z0-9]+)"
)


def _normalize_repo_rel_path(path: str) -> str:
    cleaned = path.strip().strip("'\"")
    cleaned = cleaned.replace("\\", "/")
    if "/Projects/normcore/" in cleaned:
        cleaned = cleaned.split("/Projects/normcore/", 1)[1]
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    cleaned = re.sub(r"/{2,}", "/", cleaned)
    return cleaned


def _extract_repo_file_path(command: str) -> str | None:
    if not command:
        return None
    for match in _FILE_TOKEN_RE.finditer(command):
        candidate = _normalize_repo_rel_path(match.group("path"))
        if not candidate:
            continue
        if candidate.startswith("-"):
            continue
        if "*" in candidate or "?" in candidate:
            continue
        if candidate.endswith(".pyc"):
            continue
        if candidate.startswith(".venv/"):
            continue
        return candidate
    return None


def _file_citation_key(repo_rel_path: str) -> str:
    digest = hashlib.sha256(repo_rel_path.encode("utf-8")).hexdigest()[:12]
    return f"file_{digest}"


def convert_codex_exec_events(
    path: Path,
    *,
    user_prompt: str | None = None,
    include_reasoning: bool = False,
) -> list[dict[str, Any]]:
    rows = _iter_jsonl(path)
    conversation: list[dict[str, Any]] = []
    pending_command_by_item_id: dict[str, str] = {}

    if user_prompt and user_prompt.strip():
        conversation.append({"role": "user", "content": user_prompt.strip()})

    for row in rows:
        row_type = row.get("type")
        item = row.get("item")
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")
        item_id = item.get("id")
        item_id = item_id if isinstance(item_id, str) else ""

        if row_type == "item.started" and item_type == "command_execution":
            command = item.get("command")
            if isinstance(command, str):
                pending_command_by_item_id[item_id] = command
            continue

        if row_type != "item.completed":
            continue

        if item_type == "agent_message":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                conversation.append({"role": "assistant", "content": text})
            continue

        if item_type == "reasoning":
            if include_reasoning:
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    conversation.append({"role": "assistant", "content": text})
            continue

        if item_type == "command_execution":
            command = item.get("command")
            if not isinstance(command, str):
                command = pending_command_by_item_id.get(item_id, "")
            aggregated_output = _serialize_any(item.get("aggregated_output"))
            repo_file_path = _extract_repo_file_path(command)
            if repo_file_path:
                tool_call_id = _file_citation_key(repo_file_path)
            else:
                tool_call_id = f"codex_cmd_{item_id or 'unknown'}"

            conversation.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": "shell_command",
                                "arguments": json.dumps(
                                    {"command": command}, ensure_ascii=False
                                ),
                            },
                        }
                    ],
                }
            )
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": aggregated_output,
                }
            )
            continue

    return conversation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert codex exec JSONL events to NormCore conversation JSON."
    )
    parser.add_argument("input", type=Path, help="Path to codex exec JSONL output.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for conversation JSON. Defaults to stdout.",
    )
    parser.add_argument(
        "--user-prompt",
        help="Optional user prompt text to prepend as the first user message.",
    )
    parser.add_argument(
        "--include-reasoning",
        action="store_true",
        help="Include model reasoning items as assistant messages.",
    )
    parser.add_argument(
        "--allow-non-assistant-last",
        action="store_true",
        help="Allow output where the last message role is not assistant.",
    )
    args = parser.parse_args(argv)

    conversation = convert_codex_exec_events(
        args.input,
        user_prompt=args.user_prompt,
        include_reasoning=args.include_reasoning,
    )
    if not conversation:
        raise SystemExit("No convertible events found in codex exec stream.")
    if (
        not args.allow_non_assistant_last
        and conversation[-1].get("role") != "assistant"
    ):
        raise SystemExit(
            "Last message is not assistant; this will fail evaluate(conversation=...)."
        )

    rendered = json.dumps(conversation, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {len(conversation)} messages to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
