# NormCore

NormCore implements a deterministic **normative admissibility evaluator** for agent speech acts.

Given:
- an agent utterance
- a trajectory that includes externally observed tool results

it produces an admissibility judgment under a fixed set of axioms (A4–A7).

It evaluates **participation legitimacy**, not semantic truth or task correctness.

## Specification

NormCore tracks the IETF Internet-Draft:
- [**Normative Admissibility Framework for Agent Speech Acts**](https://datatracker.ietf.org/doc/draft-romanchuk-normative-admissibility/)

Important:
- This is an Internet-Draft (work in progress), not an RFC.
- Axiom labels used in this repository (`A4`, `A5`, `A6`, `A7`) follow that draft.
- If draft wording changes in future revisions, repository behavior may be updated accordingly.

## Installation

From PyPI:

```bash
pip install normcore
```

From source:

```bash
uv sync
```

or:

```bash
pip install -e .
```

## What this is

NormCore is:
- deterministic and auditable (no embeddings, no semantic inference)
- form-based (statement modality drives the checks)
- grounding-based (licensing comes only from observed evidence)
- lexicographic (one violation makes the whole act inadmissible)

## What this is NOT

NormCore does **not**:
- verify semantic truth
- score output quality or usefulness
- infer intent, reasoning, or “why”
- do ranking / grading / reward modeling
- allow agent text to license itself

If you need “is this answer good/correct?”, this is the wrong tool.

## Hard invariants

### Grounding is tool-results-only

- Only externally observable tool outputs can become knowledge used for licensing.
- Personalization / memory / preferences / profiles are **non-epistemic** and must not become grounding.
- Personal context is accepted as metadata for audit purposes only.

## Entry point (public API)

```python
from normcore import AdmissibilityEvaluator

judgment = AdmissibilityEvaluator.evaluate(
    agent_message=agent_message,
    trajectory=trajectory,
)
```

Implementation: `src/normcore/evaluator.py`

Normative pipeline: `src/normcore/normative/`

## Inputs

`AdmissibilityEvaluator.evaluate()` consumes:
- `agent_message`: the assistant message to judge (OpenAI Chat Completions schema)
- `trajectory`: the full chat history (used only to extract tool results + build grounding)

Tool results in the trajectory are the **only** admissible source of grounding.

## Usage

```python
from normcore import AdmissibilityEvaluator

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
                "function": {"name": "get_issue", "arguments": "{\"issue_id\": 123}"},
            }
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "tool_1",
        "content": "{\"issue_id\": 123, \"status\": \"Blocked\"}",
    },
    agent_message,
]

judgment = AdmissibilityEvaluator.evaluate(agent_message=agent_message, trajectory=trajectory)
print(judgment.status)
print(judgment.licensed)
```

## CLI

Quick phrase check from terminal:

```bash
normcore evaluate --text "The deployment is blocked, so we should fix it first."
```

This command prints `AdmissibilityJudgment` as JSON.

Version:

```bash
normcore --version
```

### Personal context (non-epistemic)

```python
judgment = AdmissibilityEvaluator.evaluate(
    agent_message=agent_message,
    trajectory=trajectory,
    personal_context="prefers concise format",
    personal_context_scope="session",
    personal_context_source="user",
)
```

Personal context:
- does **not** create grounding
- does **not** permit assertive claims
- is carried for audit/trace metadata only

## Output

`evaluate()` returns `AdmissibilityJudgment` with:
- `status`: aggregated admissibility status
- `licensed`: whether grounding permitted the modality
- `can_retry`: whether reformulation is appropriate
- `statement_evaluations`: per-statement traces (modality, license, grounding)
- `violated_axioms` and `explanation`: explicit audit surface

## Pipeline (fixed)

1. Extract tool results from the trajectory
2. Build grounding (`KnowledgeStateBuilder`)
3. Extract normative participation (protocol filtered)
4. Detect modality (form-based)
5. Match candidate grounds (relevance only)
6. Derive license (sufficiency only)
7. Apply axioms A4–A7
8. Aggregate lexicographically

## Project structure

- `src/normcore/evaluator.py`: orchestration + public entrypoint
- `src/normcore/models/`: judgment + message models
- `src/normcore/normative/`: modality, grounding, licensing, axioms
- `src/normcore/cli.py`: command-line interface (`normcore`)
