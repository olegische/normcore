import json
import sys

import pytest

from normcore import AdmissibilityEvaluator
from normcore.cli import main as cli_main
from normcore.evaluator import AdmissibilityEvaluator as NamespacedEvaluator


def test_normcore_namespace_exports_evaluator():
    assert NamespacedEvaluator is AdmissibilityEvaluator


def test_normcore_cli_help_runs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["normcore"])
    assert cli_main() == 0
    output = capsys.readouterr().out
    assert "NormCore CLI" in output


def test_normcore_cli_version_runs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["normcore", "--version"])
    assert cli_main() == 0
    output = capsys.readouterr().out.strip()
    assert output


def test_normcore_cli_evaluate_runs(capsys):
    assert cli_main(["evaluate", "--agent-output", "The deployment is blocked."]) == 0
    output = capsys.readouterr().out
    assert '"status"' in output


def test_normcore_cli_evaluate_with_conversation_runs(capsys):
    conversation = [
        {"role": "user", "content": "Weather in New York?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "callWeatherNYC",
                    "type": "function",
                    "function": {"name": "get_weather", "arguments": "{\"city\":\"New York\"}"},
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

    assert cli_main(
        [
            "evaluate",
            "--conversation",
            json.dumps(conversation),
        ]
    ) == 0
    output = capsys.readouterr().out
    assert '"grounding_trace"' in output


def test_normcore_cli_evaluate_with_matching_agent_output_and_conversation_runs(capsys):
    conversation = [
        {"role": "user", "content": "Weather in New York?"},
        {"role": "assistant", "content": "Use umbrella [@callWeatherNYC]."},
    ]
    assert cli_main(
        [
            "evaluate",
            "--agent-output",
            "Use umbrella [@callWeatherNYC].",
            "--conversation",
            json.dumps(conversation),
        ]
    ) == 0
    output = capsys.readouterr().out
    assert '"status"' in output


def test_normcore_cli_evaluate_with_mismatched_agent_output_and_conversation_fails():
    conversation = [
        {"role": "user", "content": "Weather in New York?"},
        {"role": "assistant", "content": "Use umbrella [@callWeatherNYC]."},
    ]
    with pytest.raises(SystemExit):
        cli_main(
            [
                "evaluate",
                "--agent-output",
                "Different output",
                "--conversation",
                json.dumps(conversation),
            ]
        )


def test_normcore_cli_evaluate_with_external_grounds_runs(capsys):
    conversation = [
        {"role": "user", "content": "Weather in New York today vs last year?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "callWeatherNYC",
                    "type": "function",
                    "function": {"name": "get_weather", "arguments": "{\"city\":\"New York\"}"},
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
            "content": "You should carry an umbrella [@callWeatherNYC] and compare with archive [@file_weather_2025].",
        },
    ]
    grounds = [
        {
            "type": "file_citation",
            "file_id": "file_weather_2025",
            "filename": "weather_2025.txt",
            "index": 0,
        }
    ]

    assert cli_main(
        [
            "evaluate",
            "--conversation",
            json.dumps(conversation),
            "--grounds",
            json.dumps(grounds),
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    trace = payload["statement_evaluations"][0]["grounding_trace"]
    semantic_ids = {item.get("semantic_id") for item in trace}
    assert "file_weather_2025" in semantic_ids
    assert payload["grounds_accepted"] >= 2
    assert payload["grounds_cited"] >= 2


def test_normcore_cli_evaluate_with_invalid_grounds_json_fails():
    with pytest.raises(SystemExit):
        cli_main(["evaluate", "--agent-output", "Text", "--grounds", "{bad json}"])
