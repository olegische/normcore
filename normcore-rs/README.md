# NormCore (Rust)

NormCore is a deterministic **normative admissibility evaluator** for agent speech acts.

It answers one question only:

**Was the agent allowed to speak in this form, given what it observed?**

It does not evaluate semantic truth, task correctness, or answer quality.

## Specification

NormCore tracks the IETF Internet-Draft:
- [**Normative Admissibility Framework for Agent Speech Acts**](https://datatracker.ietf.org/doc/draft-romanchuk-normative-admissibility/)

Notes:
- This is an Internet-Draft (work in progress), not an RFC.
- Axiom labels in this crate (`A4`, `A5`, `A6`, `A7`) follow that draft.
- If draft wording changes, behavior may be updated in future releases.

## Install

Library:

```bash
cargo add normcore
```

CLI:

```bash
cargo install normcore
```

## How It Works

NormCore evaluates normative form and grounding, not semantic truth:

1. Extract normative statements from the assistant output.
2. Detect modality (for example assertive, conditional, refusal).
3. Build grounding only from externally observed evidence (tool results + optional external grounds).
4. Link statements to cited grounds (`[@citation_key]`).
5. Apply axioms (`A4`-`A7`) lexicographically.

A single violation is enough for an inadmissible final result.

## Hard Invariants

- Agent text cannot license itself.
- Grounding must come from externally observed evidence.
- Citations link claims to grounds by key (`[@key]`).
- Personalization/memory/profile data is non-epistemic and not grounding.

## Status Model

Top-level `AdmissibilityJudgment.status` is one of:

- `acceptable`
- `conditionally_acceptable`
- `violates_norm`
- `unsupported`
- `ill_formed`
- `underdetermined`
- `no_normative_content`

## Public API

```rust
use normcore::{evaluate, EvaluateInput};

let judgment = evaluate(EvaluateInput {
    agent_output: Some("If deployment is blocked, we should roll back.".to_string()),
    conversation: None,
    grounds: None,
})
.expect("evaluation should succeed");

assert_eq!(judgment.status.as_str(), "conditionally_acceptable");
```

## Inputs

`evaluate()` accepts:

- `agent_output` (optional): assistant output string
- `conversation` (optional): full chat history as JSON messages; last message must be assistant
- `grounds` (optional): external grounds as OpenAI-style annotations or normalized grounds

At least one of `agent_output` or `conversation` is required.
If both are provided, `agent_output` must exactly match the last assistant `content` in `conversation`.

## Minimal CLI Usage

```bash
normcore evaluate --agent-output "We should deploy now."
```

Unlicensed assertive -> expected `violates_norm`.

```bash
normcore evaluate --agent-output "If the deployment is blocked, we should roll back."
```

Conditional phrasing -> expected `conditionally_acceptable`.

```bash
normcore evaluate --conversation '[
  {"role":"assistant","content":"","tool_calls":[{"id":"callWeatherNYC","type":"function","function":{"name":"get_weather","arguments":"{\"city\":\"New York\"}"}}]},
  {"role":"tool","tool_call_id":"callWeatherNYC","content":"{\"weather_id\":\"nyc_2026-02-07\"}"},
  {"role":"assistant","content":"You should carry an umbrella [@callWeatherNYC]."}
]'
```

Grounded assertive with citation -> expected `acceptable`.

## Repository Development

Repository-focused scripts, test tracks, and from-source workflows are documented in the root README:
- [../README.md](../README.md)
