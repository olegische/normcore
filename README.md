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
- an **operational judgment gate** for grounded agent outputs

## What this is NOT

NormCore does **not**:
- verify semantic truth
- score output quality or usefulness
- infer intent, reasoning, or “why”
- do ranking / grading / reward modeling
- allow agent text to license itself
- generate code or assess code quality as such

If you need “is this answer good/correct?”, this is the wrong tool.

## Normative boundary

NormCore answers one question only:

**Was the agent allowed to speak in this form, given what it observed?**

It does not answer whether the statement is semantically true, useful, or optimal.
In practice, this targets **operational decision statements** grounded in observed
tool/file evidence, not code-generation capability evaluation.

## Why this framework exists

NormCore is intended as part of the **control plane** for agentic systems:
an explicit, deterministic gate on whether an agent is normatively allowed to
make an operational claim from observed grounds.

## Hard invariants

### Grounding is externally observable only

- Tool outputs from the trajectory can become knowledge used for licensing.
- External grounds from the public API are also allowed (for example file/url evidence from an upstream RAG pipeline).
- Grounds are linked only when the assistant text cites their `citation_key` in `[@key]` format.
- Personalization / memory / preferences / profiles are **non-epistemic** and must not become grounding.

Grounding semantics in this project:
- grounding is not truth verification
- grounding is not semantic relevance matching
- grounding is admissible observed evidence for normative licensing

## Current limitations

- **Language coverage is currently English-first for form detection.**
  Normative indicator extraction and modality heuristics are implemented with
  English lexical markers (for example `should`, `must`, `recommend`,
  `if ... then`, refusal phrases).
- Non-English outputs can be under-detected and may return `status="no_normative_content"` 
  even when the utterance is normatively meaningful.
- For now, evaluate in English when you need strict behavior, or extend
  indicator patterns in `src/normcore/normative/statement_extractor.py` and
  `src/normcore/normative/modality_detector.py` for your target language.

## Entry point (public API)

```python
from normcore import evaluate

judgment = evaluate(
    conversation=trajectory,
)
```

Implementation: `src/normcore/evaluator.py`

Normative pipeline: `src/normcore/normative/`

## Inputs

`evaluate()` consumes:
- `agent_output` (optional): assistant output string
- `conversation` (optional): full chat history as OpenAI Chat Completions message list; last message must be assistant
- `grounds` (optional): external grounds as OpenAI annotations (file/url citations)

At least one of `agent_output` or `conversation` is required.
If both are provided, `agent_output` must exactly match last assistant `content` in `conversation`.

Grounding is built from trajectory tool results plus optional external grounds.

## Usage

```python
from normcore import evaluate

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

judgment = evaluate(conversation=trajectory)
print(judgment.status)
print(judgment.licensed)
```

## Canonical examples

Unlicensed assertive (`violates_norm`):

```python
judgment = evaluate(
    conversation=[{"role": "assistant", "content": "We should deploy now."}]
)
# Expected: status="violates_norm"
```

Self-licensing attempt (`violates_norm`):

```python
judgment = evaluate(
    conversation=[{"role": "assistant", "content": "I believe we should deploy now."}]
)
# Expected: status="violates_norm" (agent text alone does not license itself)
```

Conditional downgrade (`conditionally_acceptable`):

```python
judgment = evaluate(
    conversation=[{"role": "assistant", "content": "If the deployment is blocked, we should roll back."}]
)
# Expected: status="conditionally_acceptable"
```

## CLI

Quick phrase check from terminal:

```bash
normcore evaluate --agent-output "The deployment is blocked, so we should fix it first."
```

This command prints `AdmissibilityJudgment` as JSON.

CLI parameters:
- `--log-level`: enable diagnostics in `stderr` (`CRITICAL|ERROR|WARNING|INFO|DEBUG`)
- `-v`, `-vv`: shorthand verbosity (`-v` = `INFO`, `-vv` = `DEBUG`)
- `--agent-output`: agent output text (string)
- `--conversation`: conversation history as JSON array; last item must be assistant message
- `--grounds`: grounds payload as JSON array of OpenAI annotations

Sanity rule:
- if both `--agent-output` and `--conversation` are provided, `--agent-output` must exactly match the last assistant `content` in `--conversation`.

Conversation example:

```bash
normcore evaluate --conversation '[{"role":"user","content":"Weather in New York?"},{"role":"assistant","content":"Use umbrella [@callWeatherNYC]."}]'
```

Conversation + external grounds example:

```bash
normcore evaluate \
  --conversation '[{"role":"user","content":"Weather in New York today vs last year?"},{"role":"assistant","content":"Compare today [@callWeatherNYC] and archive [@file_weather_2025]."}]' \
  --grounds '[{"type":"file_citation","file_id":"file_weather_2025","filename":"ny_weather_2025.txt","index":0}]'
```

Version:

```bash
normcore --version
```

Logging:
- Library mode is silent by default (no log handlers are configured).
- CLI diagnostics go to `stderr` so JSON in `stdout` stays machine-parseable.
- Use `-v` / `-vv`, or `--log-level`.
- `NORMCORE_LOG_LEVEL` is supported as environment fallback.

```bash
normcore -vv evaluate --agent-output "We should deploy now."
NORMCORE_LOG_LEVEL=INFO normcore evaluate --agent-output "We should deploy now."
```

## Codex smoke workflow (reproducible)

This repository includes a practical smoke path to evaluate a real `codex exec`
conversation with NormCore.

Quick run:

```bash
MODEL=gpt-5.3-codex REASONING_EFFORT=medium scripts/smoke_codex_pypi_normcore.sh
```

What this does:
- runs `codex exec --json` with a release-readiness prompt
- saves raw event stream to `context/*.jsonl`
- converts event stream to a Chat Completions-style `conversation` JSON
- runs `normcore.evaluate` on the converted conversation
- writes a final `context/*.judgment.json`

Required response shape for the Codex review prompt:
- the **first sentence** must be the publish recommendation / judgment
- all justification comes **after** that first sentence

Generated artifacts:
- `context/<run-id>.jsonl` (raw codex events)
- `context/<run-id>.stderr.log` (codex stderr)
- `context/<run-id>.conversation.json` (converted conversation for NormCore)
- `context/<run-id>.judgment.json` (NormCore output)

Manual step-by-step (same flow):

```bash
# 1) Run Codex and capture live event JSONL
echo "your prompt" | codex exec \
  --model gpt-5.3-codex \
  --cd . \
  --skip-git-repo-check \
  --json \
  -c 'effort="medium"' \
  > context/run.jsonl 2> context/run.stderr.log

# 2) Convert Codex events to NormCore conversation format
.venv/bin/python scripts/codex_exec_events_to_conversation.py \
  context/run.jsonl \
  -o context/run.conversation.json

# 3) Evaluate with NormCore
scripts/evaluate_history.sh \
  context/run.conversation.json \
  --log-level DEBUG \
  -o context/run.judgment.json
```

### File citation contract for grounding

If you want NormCore to validate file-based claims, request explicit citations in
assistant text using `[@key]`.

Recommended key format:
- `[@file_<hash12>]`
- `hash12` is first 12 hex chars of `sha256(normalized_repo_relative_file_path)`

Normalization rules for hashing:
- remove leading `./`
- use `/` separators
- hash repo-relative path

Important:
- the model should compute keys via tools (not invent them)
- the key in assistant text must match the grounding key exactly

## Output

`evaluate()` returns an `AdmissibilityJudgment` JSON object.

### Top-level fields

| Field | Meaning |
|---|---|
| `status` | Final verdict for the whole response. |
| `licensed` | Whether grounding permitted the chosen normative form(s). |
| `can_retry` | Whether reformulation is recommended. |
| `statement_evaluations` | Per-statement trace (how each statement was judged). |
| `feedback_hint` | Optional retry hint when reformulation is useful. |
| `violated_axioms` | List of violated axioms at aggregate level. |
| `explanation` | Human-readable summary of final verdict. |
| `num_statements` | Count of evaluated normative statements. |
| `num_acceptable` | Count of statements with acceptable outcomes. |
| `grounds_accepted` | Count of grounds admitted into the evidence pool. |
| `grounds_cited` | Count of admitted grounds actually cited in text (`[@key]`). |

### `statement_evaluations[]` fields

| Field | Meaning |
|---|---|
| `statement_id` | Stable statement identifier (`final_response` or `refusal`). |
| `statement` | Statement text that was evaluated. |
| `modality` | Detected modality (`assertive`, `conditional`, `refusal`, `descriptive`). |
| `license` | Modalities permitted by current grounding. |
| `status` | Verdict for this statement. |
| `violated_axiom` | Violated axiom for this statement, if any. |
| `explanation` | Human-readable reason for this statement verdict. |
| `grounding_trace` | Evidence nodes considered for this statement. |
| `subject` / `predicate` | Internal normalized statement shape. |

### `grounding_trace[]` fields

| Field | Meaning |
|---|---|
| `id` | Internal ground node ID. |
| `scope` | Ground scope (currently factual in runtime flow). |
| `source` | Ground source class (for example observed). |
| `status` | Ground node status (for example confirmed). |
| `confidence` | Numeric confidence value attached to node. |
| `strength` | Node strength label used by licensing logic. |
| `semantic_id` | External/semantic ID used for link resolution. |

### How to read common outcomes

- `status="acceptable"` + `licensed=true` + `can_retry=false`: response is normatively admissible as-is.
- `status="conditionally_acceptable"` + `licensed=true`: agent used conditional framing and stayed within license.
- `status="unsupported"` + `can_retry=true`: missing/insufficient grounding; ask for more context or weaken claim form.
- `status="violates_norm"` + `can_retry=true`: hard normative violation (for example unlicensed assertive claim).
- `status="no_normative_content"`: protocol-only response; no normative claim was evaluated.

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
