# normcore-rs

Rust implementation of NormCore placed alongside Python package at `/Users/olegromanchuk/Projects/normcore/src/normcore`.

Implemented capabilities:
- public evaluator API with Python-compatible contract (`agent_output`, `conversation`, `grounds`)
- deterministic normative pipeline: statement extraction -> modality detection -> ground matching -> license derivation -> axiom check -> aggregate judgment
- citations subsystem (`[@key]`, grounds coercion, OpenAI-style citation adapter)
- internal JSON parser/serializer (no external dependencies)
- CLI command with `evaluate`, `--agent-output`, `--conversation`, `--grounds`, `--version`, `-v/-vv`, `--log-level`

Run:

```bash
cargo test
cargo run -- evaluate --agent-output "We should deploy now."
```
