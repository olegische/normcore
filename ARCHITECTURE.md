# Architecture

This document describes the high-level architecture of the NormCore repository, with focus on the Rust implementation in `normcore-rs`.

## Bird's-Eye View

NormCore is a deterministic evaluator of **normative admissibility** for agent speech acts.

Core question:

- Was the agent allowed to speak in this form, given available observed evidence?

NormCore is intentionally narrow:

- It does not score semantic correctness.
- It does not score output quality.
- It does not infer hidden intent.

The architecture is built around a sans-IO pipeline: parse input data, derive grounding and modality, derive licensing, check axioms, aggregate to a single judgment.

## Repository Code Map

- `normcore-rs`
  - Rust implementation (library + CLI)
- `normcore-py`
  - Python implementation
- `formal`
  - Formal models and traces used for replay checks
- `scripts`
  - Operational wrappers for tests and checks

## Rust Code Map (`normcore-rs`)

Entry points:

- `src/lib.rs`: public Rust API exports
- `src/main.rs`: CLI front-end and argument handling

Core modules:

- `src/evaluator.rs`
  - Public API orchestration (`evaluate`, `evaluate_from_json`, conversation parsing)
  - End-to-end evaluation pipeline and final aggregation
- `src/normative/*`
  - Normative core logic:
    - `extractor.rs`: statement extraction and protocol-text stripping
    - `modality_detector.rs`: modality classification
    - `knowledge_builder.rs`: convert tool outputs and grounds into knowledge nodes
    - `ground_matcher.rs`: statement-to-ground scope filtering
    - `license_deriver.rs`: derive permitted modalities from grounding
    - `axiom_checker.rs`: apply axioms A4-A7 per statement
    - `models.rs`: normative domain model
- `src/citations.rs`
  - Citation extraction, ground coercion, and link materialization
- `src/models.rs`
  - External/public data model and judgment schema
- `src/json.rs`
  - Lightweight JSON parser/value model used by core

Test surfaces:

- `tests/evaluate_scenarios.rs`: public API behavior scenarios
- `tests/golden_corpus.rs` + `tests/fixtures/golden_corpus.json`: corpus regression
- `tests/trace_replay.rs` + `tests/fixtures/trace_replay.json`: formal trace replay
- `tests/property_invariants.rs`: property-based invariants
- `fuzz/fuzz_targets/*`: fuzz entry points

## Evaluation Pipeline

`evaluate(EvaluateInput)` in `src/evaluator.rs` is the composition boundary.

High-level flow:

1. Normalize input (`agent_output` and/or `conversation`).
2. Extract agent message and trajectory.
3. Extract tool-result speech acts from trajectory.
4. Build knowledge nodes from tool outputs and external grounds.
5. Build statement-ground links from in-text citations and ground set.
6. Extract statements from agent text.
7. Detect modality and conditions.
8. Match applicable grounds per statement.
9. Derive license from grounds/links.
10. Run axiom checks.
11. Aggregate statement results into final admissibility judgment.

## Architecture Invariants

The following constraints are intentionally stable and should be preserved.

1. Core logic is deterministic.
- For equal input data, output must be identical.
- No network calls, clock-based behavior, or randomness in evaluator core.

2. Core evaluator is sans-IO.
- IO concerns live at boundaries (`src/main.rs`, tests, scripts).
- Normative modules operate on in-memory data structures.

3. Licensing is evidence-driven.
- Agent text cannot self-license.
- Licensing depends on derived grounds/links and normative rules.

4. Public boundary is data-in/data-out.
- Main library boundary is `evaluate` / `evaluate_from_json`.
- Internal modules are implementation details and may evolve.

5. Axiom labels are externally meaningful.
- `A4`, `A5`, `A6`, `A7` are part of the observed contract and must remain explicit in outputs when violated.

## Testing Strategy

NormCore intentionally uses a mixed strategy:

1. Visible unit tests near implementation (`#[cfg(test)]` in `src/*`).
- Rationale: fast local feedback, explicit local invariants, and high visibility for AI-assisted development.

2. Boundary tests on public APIs (`tests/*`).
- Rationale: catch composition/integration regressions that unit tests cannot see.
- These tests validate externally observable behavior, not internal helper wiring.

3. Data-driven regression fixtures.
- Golden corpus and formal replay fixtures keep behavior stable across refactors.

4. Invariant and robustness tracks.
- Property tests (`proptest`), fuzz tests (`cargo-fuzz`), mutation tests (`cargo-mutants`).

### Why Boundary Tests Are Still Needed

Even with extensive unit tests, boundary tests remain essential for:

- API contract consistency (`evaluate`/`evaluate_from_json`/CLI paths).
- Cross-module interaction errors.
- Schema compatibility and end-to-end output semantics.

Unit tests protect local logic; boundary tests protect the product contract.

## Position on Expect/Snapshot Tests

Current state:

- The project already uses externalized, data-driven expectations (`golden_corpus.json`, `trace_replay.json`).
- Assertions target contract fields explicitly (status, license flags, axioms, counters).

Decision now:

- Do not introduce `expect-test`/`insta` yet.

Reason:

- Current fixtures already provide low-cost bulk updates and clear diffs.
- Snapshotting full outputs would add maintenance surface without strong immediate payoff.

When to introduce snapshots:

- If output payloads become much larger and high-churn.
- If many tests begin to fail only due to broad formatting/shape shifts where bulk-approved updates are desired.

## Change Guidance

When editing behavior in `normcore-rs`:

1. Prefer preserving public boundary (`evaluate`, `evaluate_from_json`) and evolve internals behind it.
2. Update fixture-driven tests when normative behavior intentionally changes.
3. Keep unit tests close to modified modules for local invariants.
4. Keep at least one boundary regression that exercises the changed behavior end-to-end.
