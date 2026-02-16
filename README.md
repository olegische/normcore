# NormCore

NormCore is a deterministic normative admissibility evaluator for agent speech acts.

It evaluates one question only:

**Was the agent allowed to speak in this form, given what it observed?**

It does not score semantic correctness or response quality.

## Implementations

- Python package (`src/normcore`)
  - PyPI package: `normcore`
  - Docs: [`src/normcore/README.md`](src/normcore/README.md)
- Rust crate (`src/normcore-rs`)
  - Crate package: `normcore-rs`
  - Docs: [`src/normcore-rs/README.md`](src/normcore-rs/README.md)

## Specification

NormCore tracks the IETF Internet-Draft:
- [Normative Admissibility Framework for Agent Speech Acts](https://datatracker.ietf.org/doc/draft-romanchuk-normative-admissibility/)

Notes:
- This is an Internet-Draft (work in progress), not an RFC.
- Axiom labels in this repo (`A4`, `A5`, `A6`, `A7`) follow that draft.

## Repository Layout

- `src/normcore` — Python implementation
- `src/normcore-rs` — Rust implementation
- `formal` — formal specs and artifacts
- `scripts` — evaluation and smoke scripts

## Quick Start

Python:

```bash
pip install normcore
normcore evaluate --agent-output "We should deploy now."
```

Rust (from source):

```bash
cargo run --manifest-path src/normcore-rs/Cargo.toml -- evaluate --agent-output "We should deploy now."
```

## License

Apache-2.0.
