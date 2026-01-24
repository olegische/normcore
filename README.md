# NormCore

NormCore is a deterministic, auditable evaluator for agent speech acts. It judges whether a
response is normatively admissible based on **form** (modality) and **grounding**, not on
semantic truth or task correctness. The design is intentionally non-semantic, fully traceable,
and safe against self-licensing via personalization context.

## Documentation

This repository is intentionally small. The main entrypoint is
`evaluator.evaluator.AdmissibilityEvaluator`. The normative pipeline is implemented under
`src/evaluator/normative/`.

## Installation

```sh
# editable install from source
pip install -e .
```

If you publish to PyPI, users can install with:

```sh
pip install normcore
```

## Usage

The evaluator consumes OpenAI-style chat messages (via `openai.types.chat` schemas) and a
single assistant message to validate. Tool results in the trajectory are the *only* source of
grounding.

```python
from evaluator.evaluator import AdmissibilityEvaluator

agent_message = {
    "role": "assistant",
    "content": "Issue 123 is blocked, so we should fix it first.",
}

trajectory = [
    {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "tool_1",
                "type": "function",
                "function": {
                    "name": "get_issue",
                    "arguments": "{\"issue_id\": 123}",
                },
            },
            {
                "id": "tool_2",
                "type": "function",
                "function": {
                    "name": "get_issue_dependencies",
                    "arguments": "{\"issue_id\": 123}",
                },
            }
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "tool_1",
        "content": "{\"issue_id\": 123, \"status\": \"Blocked\"}",
    },
    {
        "role": "tool",
        "tool_call_id": "tool_2",
        "content": "[{\"issue_id\": 98, \"status\": \"Open\"}]",
    },
    {
        "role": "assistant",
        "content": "Issue 123 is blocked, so we should fix it first.",
    },
]

judgment = AdmissibilityEvaluator.evaluate(
    agent_message=agent_message,
    trajectory=trajectory,
)

print(judgment.status)
print(judgment.licensed)
print(judgment.statement_evaluations)
```

### Personal context (non-epistemic)

Personal context can be passed for audit metadata, but it **never** contributes to grounding
or assertive licensing:

```python
judgment = AdmissibilityEvaluator.evaluate(
    agent_message=agent_message,
    trajectory=trajectory,
    personal_context="preferred format: concise",
    personal_context_scope="session",
    personal_context_source="user",
)
```

## Outputs

`AdmissibilityEvaluator.evaluate()` returns an `AdmissibilityJudgment` with:

- `status`: aggregated admissibility status
- `licensed`: whether grounding yielded a license
- `can_retry`: whether a retry is suggested
- `statement_evaluations`: per-statement traces (modality, license, grounding)
- `violated_axioms` and `explanation` for auditability

## How it works (pipeline)

1. **Extract tool results** from the trajectory (observer-only grounding).
2. **Build GroundSet** from tool results (`KnowledgeStateBuilder`).
3. **Extract normative participation** from assistant output (`StatementExtractor`).
4. **Detect modality** (assertive/conditional/refusal/descriptive).
5. **Match candidate grounds** by scope (`GroundSetMatcher`).
6. **Derive license** from grounding (`LicenseDeriver`).
7. **Apply axioms A4–A7** (`AxiomChecker`).
8. **Aggregate** to a single admissibility judgment (lexicographic).

## Design principles (summary)

- **Deterministic & auditable**: no embeddings, no semantic inference.
- **Form-based**: modality is derived from formal indicators.
- **Grounding-only licensing**: only externally observed tool results grant assertive license.
- **Personal context is non-epistemic**: personalization never grants grounding.
- **Lexicographic aggregation**: any violation makes the whole act inadmissible.

## Project structure

- `src/evaluator/evaluator.py`: public entrypoint and orchestration
- `src/evaluator/models/`: public and internal message/judgment models
- `src/evaluator/normative/`: modality, grounding, licensing, and axiom logic
