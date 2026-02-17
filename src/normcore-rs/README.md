# NormCore (Rust)

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

From source (this repository):

```bash
cargo test --manifest-path src/normcore-rs/Cargo.toml
```

Install CLI binary locally:

```bash
cargo install --path src/normcore-rs
```

After installation, run:

```bash
normcore-rs --version
normcore-rs evaluate --agent-output "The deployment is blocked, so we should fix it first."
```

Without install, you can run directly with Cargo:

```bash
cargo run --manifest-path src/normcore-rs/Cargo.toml -- evaluate --agent-output "The deployment is blocked, so we should fix it first."
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
- infer intent, reasoning, or "why"
- do ranking / grading / reward modeling
- allow agent text to license itself
- generate code or assess code quality as such

If you need "is this answer good/correct?", this is the wrong tool.

## Normative boundary

NormCore answers one question only:

**Was the agent allowed to speak in this form, given what it observed?**

It does not answer whether the statement is semantically true, useful, or optimal.
In practice, this targets **operational decision statements** grounded in observed
tool/file evidence, not code-generation capability evaluation.

## Entry points (public API)

Rust library:

```rust
use normcore_rs::{evaluate, EvaluateInput};

let judgment = evaluate(EvaluateInput {
    agent_output: Some("If deployment is blocked, we should roll back.".to_string()),
    conversation: None,
    grounds: None,
})
.expect("evaluation should succeed");

assert_eq!(judgment.status.as_str(), "conditionally_acceptable");
```

CLI:

```bash
normcore-rs evaluate --agent-output "We should deploy now."
```

## Inputs

`evaluate()` consumes:
- `agent_output` (optional): assistant output string
- `conversation` (optional): full chat history as JSON messages; last message must be assistant
- `grounds` (optional): external grounds as OpenAI-style annotations or normalized grounds

At least one of `agent_output` or `conversation` is required.
If both are provided, `agent_output` must exactly match last assistant `content` in `conversation`.

Grounding is built from trajectory tool results plus optional external grounds.

## Canonical examples

Unlicensed assertive (`violates_norm`):

```bash
normcore-rs evaluate --agent-output "We should deploy now."
```

Conditional downgrade (`conditionally_acceptable`):

```bash
normcore-rs evaluate --agent-output "If the deployment is blocked, we should roll back."
```

Grounded assertive via conversation + citation (`acceptable`):

```bash
normcore-rs evaluate --conversation '[
  {"role":"assistant","content":"","tool_calls":[{"id":"callWeatherNYC","type":"function","function":{"name":"get_weather","arguments":"{\"city\":\"New York\"}"}}]},
  {"role":"tool","tool_call_id":"callWeatherNYC","content":"{\"weather_id\":\"nyc_2026-02-07\"}"},
  {"role":"assistant","content":"You should carry an umbrella [@callWeatherNYC]."}
]'
```

## CLI parameters

- `--log-level`: accepted for CLI parity (`CRITICAL|ERROR|WARNING|INFO|DEBUG`)
- `-v`, `-vv`: accepted verbosity flags
- `--agent-output`: agent output text (string)
- `--conversation`: conversation history as JSON array; last item must be assistant message
- `--grounds`: grounds payload as JSON array

Sanity rule:
- if both `--agent-output` and `--conversation` are provided, `--agent-output` must exactly match the last assistant `content` in `--conversation`.

## Scripted checks (repo)

Rust-focused evaluation scripts are in:
- `scripts/rust/evaluate_history_rs.sh`
- `scripts/rust/check_grounds_weather_ny_rs.sh`
- `scripts/rust/check_external_grounds_weather_history_rs.sh`

Example:

```bash
scripts/rust/check_grounds_weather_ny_rs.sh
scripts/rust/check_external_grounds_weather_history_rs.sh
```

## Rust Test Tracks

This crate includes five complementary Rust-only testing tracks:

1. Property-based invariants (`proptest`):
   - `/Users/olegromanchuk/Projects/normcore/src/normcore-rs/tests/property_invariants.rs`
2. Golden scenario corpus regression:
   - `/Users/olegromanchuk/Projects/normcore/src/normcore-rs/tests/golden_corpus.rs`
   - `/Users/olegromanchuk/Projects/normcore/src/normcore-rs/tests/fixtures/golden_corpus.json`
3. Formal trace replay regression:
   - `/Users/olegromanchuk/Projects/normcore/src/normcore-rs/tests/trace_replay.rs`
   - `/Users/olegromanchuk/Projects/normcore/src/normcore-rs/tests/fixtures/trace_replay.json`
4. Mutation testing (`cargo-mutants`):
   - `just rust-mutants`
   - wrapper script: `/Users/olegromanchuk/Projects/normcore/scripts/rust/run_mutants_rs.sh`
5. Fuzz testing (`cargo-fuzz`):
   - `just rust-fuzz fuzz_parse_json 5000`
   - `just rust-fuzz fuzz_parse_conversation 5000`
   - `just rust-fuzz fuzz_extract_citation_keys 5000`
   - wrapper script: `/Users/olegromanchuk/Projects/normcore/scripts/rust/run_fuzz_rs.sh`
   - fuzz crate: `/Users/olegromanchuk/Projects/normcore/src/normcore-rs/fuzz/Cargo.toml`
