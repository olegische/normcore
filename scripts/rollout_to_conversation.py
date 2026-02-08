#!/usr/bin/env python3
"""
Convert Codex rollout JSONL into a NormCore-compatible conversation JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
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
        if not isinstance(obj, dict):
            continue
        rows.append(obj)
    return rows


def _extract_message_text(payload: dict[str, Any]) -> str:
    text_parts: list[str] = []
    content = payload.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") not in {"input_text", "output_text"}:
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text)
    return "\n".join(text_parts).strip()


def _from_event_messages(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    conversation: list[dict[str, str]] = []
    for row in rows:
        if row.get("type") != "event_msg":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        kind = payload.get("type")
        if kind not in {"user_message", "agent_message"}:
            continue
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            continue
        role = "user" if kind == "user_message" else "assistant"
        conversation.append({"role": role, "content": message})
    return conversation


def _from_response_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conversation: list[dict[str, Any]] = []
    for row in rows:
        if row.get("type") != "response_item":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            continue
        text = _extract_message_text(payload)
        if text:
            conversation.append({"role": role, "content": text})
    return conversation


def _serialize_any(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False)


def _from_event_and_tools(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build conversation from user/assistant event messages + tool traces.

    Tool traces are reconstructed from response_item(function_call +
    function_call_output) records as OpenAI-style assistant/tool messages.
    """
    conversation: list[dict[str, Any]] = []
    started = False
    pending_event_agent: str | None = None

    for row in rows:
        row_type = row.get("type")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue

        if row_type == "event_msg":
            kind = payload.get("type")
            if kind == "user_message":
                message = payload.get("message")
                if isinstance(message, str) and message.strip():
                    started = True
                    if pending_event_agent:
                        conversation.append(
                            {"role": "assistant", "content": pending_event_agent}
                        )
                        pending_event_agent = None
                    conversation.append({"role": "user", "content": message})
                continue
            if kind == "agent_message" and started:
                message = payload.get("message")
                if isinstance(message, str) and message.strip():
                    pending_event_agent = message
                continue

        if not started or row_type != "response_item":
            continue

        item_type = payload.get("type")
        if item_type == "function_call":
            call_id = payload.get("call_id")
            name = payload.get("name")
            if not isinstance(call_id, str) or not isinstance(name, str):
                continue
            arguments = _serialize_any(payload.get("arguments"))
            conversation.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": arguments},
                        }
                    ],
                }
            )
            continue

        if item_type == "function_call_output":
            call_id = payload.get("call_id")
            if not isinstance(call_id, str):
                continue
            output = _serialize_any(payload.get("output"))
            conversation.append(
                {"role": "tool", "tool_call_id": call_id, "content": output}
            )
            continue

        if item_type == "message" and payload.get("role") == "assistant":
            text = _extract_message_text(payload)
            if text:
                conversation.append({"role": "assistant", "content": text})
                pending_event_agent = None

    if pending_event_agent:
        conversation.append({"role": "assistant", "content": pending_event_agent})
    return conversation


def convert_rollout(path: Path, include_tools: bool = True) -> list[dict[str, Any]]:
    rows = _iter_jsonl(path)
    conversation = _from_event_and_tools(rows) if include_tools else _from_event_messages(rows)
    if conversation:
        return conversation
    return _from_response_messages(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert rollout JSONL into NormCore conversation JSON."
    )
    parser.add_argument("input", type=Path, help="Path to rollout JSONL file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for conversation JSON. Defaults to stdout.",
    )
    parser.add_argument(
        "--messages-only",
        action="store_true",
        help="Build conversation from user/assistant messages only (no tool traces).",
    )
    parser.add_argument(
        "--allow-non-assistant-last",
        action="store_true",
        help="Allow output where the last message role is not assistant.",
    )
    args = parser.parse_args(argv)

    conversation = convert_rollout(args.input, include_tools=not args.messages_only)
    if not conversation:
        raise SystemExit("No user/assistant messages found in rollout.")
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
        print(
            f"Wrote {len(conversation)} messages to {args.output}",
            file=sys.stderr,
        )
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
