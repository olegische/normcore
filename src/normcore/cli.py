"""
Command line entry point for NormCore.
"""

from __future__ import annotations

import argparse
import json
from importlib.metadata import PackageNotFoundError, version

from normcore.evaluator import evaluate
from normcore.logging import configure_logging


def _resolve_log_level(args: argparse.Namespace) -> str | None:
    log_level = getattr(args, "log_level", None)
    if isinstance(log_level, str) and log_level:
        return log_level
    verbose = getattr(args, "verbose", 0)
    if not isinstance(verbose, int):
        return None
    if verbose >= 2:
        return "DEBUG"
    if verbose == 1:
        return "INFO"
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="normcore",
        description="NormCore CLI.",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Enable CLI diagnostics at selected log level (printed to stderr).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase diagnostics verbosity (-v=INFO, -vv=DEBUG).",
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
    configure_logging(level=_resolve_log_level(args))

    if args.version:
        try:
            print(version("normcore"))
        except PackageNotFoundError:
            print("normcore (not installed)")
        return 0

    if args.command == "evaluate":
        conversation = None
        if args.conversation:
            try:
                conversation = json.loads(args.conversation)
            except json.JSONDecodeError as exc:
                parser.error(f"Failed to parse --conversation JSON: {exc}")

        grounds = None
        if args.grounds:
            try:
                grounds = json.loads(args.grounds)
            except json.JSONDecodeError as exc:
                parser.error(f"Failed to parse --grounds JSON: {exc}")

        try:
            judgment = evaluate(
                agent_output=args.agent_output,
                conversation=conversation,
                grounds=grounds,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(judgment.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
