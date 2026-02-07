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
        "--text",
        required=True,
        help="Assistant phrase to evaluate.",
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
        agent_message = {
            "role": "assistant",
            "content": args.text,
        }
        judgment = AdmissibilityEvaluator.evaluate(
            agent_message=agent_message,
            trajectory=[agent_message],
        )
        print(json.dumps(judgment.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
