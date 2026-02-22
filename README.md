# NormCore

NormCore is a deterministic normative admissibility evaluator for agent speech acts.

It evaluates one question only:

**Was the agent allowed to speak in this form, given what it observed?**

It does not score semantic correctness or response quality.

## Implementations

- Python package (`normcore-py/src/normcore`)
  - PyPI package: `normcore`
  - Docs: [`normcore-py/README.md`](normcore-py/README.md)
- Rust crate (`normcore-rs`)
  - Crate package: `normcore`
  - Docs: [`normcore-rs/README.md`](normcore-rs/README.md)

## Specification

NormCore tracks the IETF Internet-Draft:
- [Normative Admissibility Framework for Agent Speech Acts](https://datatracker.ietf.org/doc/draft-romanchuk-normative-admissibility/)

Notes:
- This is an Internet-Draft (work in progress), not an RFC.
- Axiom labels in this repo (`A4`, `A5`, `A6`, `A7`) follow that draft.

## Repository Layout

- `ARCHITECTURE.md` - high-level architecture and testing strategy
- `normcore-py/src/normcore` - Python implementation
- `normcore-rs` - Rust implementation
- `formal` - formal specs and artifacts
- `scripts` - evaluation and smoke scripts

## Quick Start

Python:

```bash
pip install normcore
normcore evaluate --agent-output "We should deploy now."
```

Rust (crate install):

```bash
cargo install normcore
normcore evaluate --agent-output "We should deploy now."
```

Rust (from source in this repo):

```bash
cargo run --manifest-path normcore-rs/Cargo.toml -- evaluate --agent-output "We should deploy now."
```

## Rust Development (Repository)

These commands are for contributors working in this monorepo.

### Installation / Local Run (from source)

```bash
cargo test --manifest-path normcore-rs/Cargo.toml
cargo install --path normcore-rs
normcore --version
normcore evaluate --agent-output "The deployment is blocked, so we should fix it first."
```

### Scripted checks (repo)

Rust-focused evaluation scripts:

- `scripts/rust/evaluate_history_rs.sh`
- `scripts/rust/run_normcore_rs_eval.sh`
- `scripts/rust/smoke_codex_rust_local.sh`

Examples:

```bash
scripts/rust/run_normcore_rs_eval.sh "The deployment is blocked."
scripts/rust/evaluate_history_rs.sh context/rollout.conversation.json -o context/judgment.rs.json
```

### Rust test tracks

1. Property-based invariants (`proptest`):
   - `normcore-rs/tests/property_invariants.rs`
2. Golden scenario corpus regression:
   - `normcore-rs/tests/golden_corpus.rs`
   - `normcore-rs/tests/fixtures/golden_corpus.json`
3. Formal trace replay regression:
   - `normcore-rs/tests/trace_replay.rs`
   - `normcore-rs/tests/fixtures/trace_replay.json`
4. Mutation testing (`cargo-mutants`):
   - `just rust-mutants`
   - wrapper script: `scripts/rust/run_mutants_rs.sh`
5. Fuzz testing (`cargo-fuzz`):
   - `just rust-fuzz fuzz_parse_json 5000`
   - `just rust-fuzz fuzz_parse_conversation 5000`
   - `just rust-fuzz fuzz_extract_citation_keys 5000`
   - wrapper script: `scripts/rust/run_fuzz_rs.sh`
   - fuzz crate: `normcore-rs/fuzz/Cargo.toml`

## License

Apache-2.0.
