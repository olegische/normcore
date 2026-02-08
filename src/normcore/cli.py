"""
Command line entry point for NormCore.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import PackageNotFoundError, version

from normcore import AdmissibilityEvaluator


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="normcore",
        description="NormCore CLI.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed NormCore version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")
    evaluate = subparsers.add_parser(
        "evaluate",
        help="Evaluate one assistant phrase for normative admissibility.",
    )
    evaluate.add_argument(
        "--agent-output",
        help="Agent output text (string).",
    )
    evaluate.add_argument(
        "--conversation",
        help=(
            "Conversation history as JSON array. Last item must be assistant message. "
            "If --agent-output is also provided, it must match the last assistant content."
        ),
    )
    evaluate.add_argument(
        "--grounds",
        help="Grounds payload as JSON array of OpenAI annotations.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        try:
            print(version("normcore"))
        except PackageNotFoundError:
            print("normcore (not installed)")
        return 0

    if args.command == "evaluate":
        if not args.agent_output and not args.conversation:
            parser.error("evaluate requires --agent-output or --conversation")

        try:
            if args.conversation:
                conversation = json.loads(args.conversation)
                if not isinstance(conversation, list) or not conversation:
                    parser.error("--conversation must be a non-empty JSON array")
                trajectory = conversation
                agent_message = trajectory[-1]
                if not isinstance(agent_message, dict) or agent_message.get("role") != "assistant":
                    parser.error("Last conversation item must be an assistant message")
                if args.agent_output is not None:
                    if not isinstance(agent_message.get("content"), str):
                        parser.error(
                            "Last conversation assistant content must be a string when --agent-output is provided"
                        )
                    if agent_message["content"] != args.agent_output:
                        parser.error(
                            "--agent-output must match the last assistant content in --conversation"
                        )
            else:
                agent_message = {
                    "role": "assistant",
                    "content": args.agent_output,
                }
                trajectory = [agent_message]
        except json.JSONDecodeError as exc:
            parser.error(f"Failed to parse --conversation JSON: {exc}")

        grounds = None
        if args.grounds:
            try:
                grounds = json.loads(args.grounds)
            except json.JSONDecodeError as exc:
                parser.error(f"Failed to parse --grounds JSON: {exc}")

        judgment = AdmissibilityEvaluator.evaluate(
            agent_message=agent_message,
            trajectory=trajectory,
            grounds=grounds,
        )
        print(json.dumps(judgment.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
