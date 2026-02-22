import pytest

from normcore.evaluator import evaluate


def test_evaluate_requires_agent_output_or_conversation():
    with pytest.raises(ValueError, match="requires agent_output or conversation"):
        evaluate()


def test_evaluate_rejects_non_list_or_empty_conversation():
    with pytest.raises(ValueError, match="non-empty list"):
        evaluate(conversation={"role": "assistant", "content": "x"})

    with pytest.raises(ValueError, match="non-empty list"):
        evaluate(conversation=[])


def test_evaluate_requires_last_conversation_item_to_be_assistant():
    with pytest.raises(ValueError, match="assistant message"):
        evaluate(conversation=[{"role": "user", "content": "x"}])


def test_evaluate_requires_string_content_when_agent_output_is_provided():
    conversation = [
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "x"}],
        }
    ]
    with pytest.raises(ValueError, match="content must be a string"):
        evaluate(agent_output="x", conversation=conversation)


def test_evaluate_refusal_conversation_uses_refusal_path():
    conversation = [
        {"role": "user", "content": "Can we ship now?"},
        {
            "role": "assistant",
            "content": [{"type": "refusal", "refusal": "I would not publish yet."}],
        },
    ]

    judgment = evaluate(conversation=conversation)

    assert judgment.statement_evaluations
    assert judgment.statement_evaluations[0].statement_id == "refusal"
