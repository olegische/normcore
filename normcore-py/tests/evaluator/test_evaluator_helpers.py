import json

import pytest

from normcore.evaluator import AdmissibilityEvaluator
from normcore.models.messages import _AssistantMessage, _TextPart


def test_parse_tool_args():
    evaluator = AdmissibilityEvaluator()
    assert evaluator._parse_tool_args(None) == {}
    assert evaluator._parse_tool_args({"a": 1}) == {"a": 1}
    assert evaluator._parse_tool_args('{"a": 1}') == {"a": 1}
    assert evaluator._parse_tool_args("not json") == {}
    assert evaluator._parse_tool_args(123) == {}


def test_extract_text_content_variants():
    evaluator = AdmissibilityEvaluator()
    assert evaluator._extract_text_content(None) == ""
    assert evaluator._extract_text_content("hi") == "hi"
    parts = [_TextPart(type="text", text="a"), _TextPart(type="text", text="b")]
    assert evaluator._extract_text_content(parts) == "ab"
    with pytest.raises(ValueError):
        evaluator._extract_text_content(123)


def test_map_tool_message_rejects_refusal_parts():
    evaluator = AdmissibilityEvaluator()
    msg = {
        "role": "tool",
        "tool_call_id": "1",
        "content": [{"type": "refusal", "refusal": "no"}],
    }
    with pytest.raises(ValueError):
        evaluator._map_tool_message(msg)


def test_to_speech_act_text_and_refusal():
    evaluator = AdmissibilityEvaluator()
    msg_text = {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}
    assistant = evaluator._map_assistant_message(msg_text)
    speech = evaluator._to_speech_act(assistant)
    assert hasattr(speech, "text") and speech.text == "hi"

    msg_refusal = {"role": "assistant", "content": [{"type": "refusal", "refusal": "no"}]}
    assistant = evaluator._map_assistant_message(msg_refusal)
    speech = evaluator._to_speech_act(assistant)
    assert hasattr(speech, "refusal") and speech.refusal == "no"

    msg_mixed = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "hi"},
            {"type": "refusal", "refusal": "no"},
        ],
    }
    assistant = evaluator._map_assistant_message(msg_mixed)
    with pytest.raises(ValueError):
        evaluator._to_speech_act(assistant)


def test_extract_tool_results_from_trajectory():
    evaluator = AdmissibilityEvaluator()
    trajectory = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call1",
                    "type": "function",
                    "function": {"name": "search", "arguments": json.dumps({"q": "x"})},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call1", "content": "result"},
        {"role": "function", "name": "legacy", "content": "ok"},
    ]

    results = evaluator._extract_tool_results(trajectory)
    assert len(results) == 2
    assert results[0].tool_name == "search"
    assert results[0].arguments == {"q": "x"}
    assert results[0].result_text == "result"
    assert results[1].tool_name == "legacy"
    assert results[1].result_text == "ok"


def test_map_tool_call_custom():
    evaluator = AdmissibilityEvaluator()
    tool_call = {
        "id": "call1",
        "type": "custom",
        "custom": {"name": "my_tool", "input": "x"},
    }
    mapped = evaluator._map_tool_call(tool_call)
    assert mapped.name == "my_tool"


def test_map_content_none_and_unsupported_type():
    evaluator = AdmissibilityEvaluator()
    assert evaluator._map_content(None) is None
    with pytest.raises(ValueError):
        evaluator._map_content(123)


def test_map_tool_call_unsupported_type_raises():
    evaluator = AdmissibilityEvaluator()
    with pytest.raises(ValueError):
        evaluator._map_tool_call({"id": "x", "type": "unknown"})


def test_to_speech_act_handles_none_content_and_unsupported_content_type():
    evaluator = AdmissibilityEvaluator()
    assistant_none = evaluator._map_assistant_message({"role": "assistant", "content": None})
    speech = evaluator._to_speech_act(assistant_none)
    assert hasattr(speech, "text") and speech.text == ""

    bad_assistant = _AssistantMessage.model_construct(content=123, tool_calls=[])
    with pytest.raises(ValueError):
        evaluator._to_speech_act(bad_assistant)
