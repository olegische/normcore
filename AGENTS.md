# Rust / normcore-rs

This file defines coding and testing rules for Rust code in this repository.

Scope:
- Main Rust crate: `src/normcore-rs`
- These rules apply to all Rust source, tests, and Rust tooling changes.

## Working Style

- Use `just` commands from repository root whenever possible.
- Prefer modifying existing modules over introducing ad-hoc one-off helpers.
- Do not create helper functions referenced only once unless it clearly improves readability.

## Required Commands After Rust Changes

Run these automatically after any Rust code change:

1. `just fmt`
2. `just clippy-strict`
3. `just test`

For targeted local iteration, you may run crate-level commands directly in `src/normcore-rs`, but final verification should still pass through the commands above.

## Lint and Style Rules

- Clippy warnings are treated as errors in Rust CI (`-D warnings`).
- Always collapse nested `if`/`if let` when clippy suggests (`collapsible_if`).
- Always inline `format!` args where possible (`uninlined_format_args`).
- Prefer method references over redundant closures where readable (`redundant_closure_for_method_calls`).
- Prefer exhaustive `match` arms where practical; avoid wildcard arms that hide new variants.
- Keep modules responsibility-focused and reasonably small.

## Testing Rules

- Prefer behavior-first tests through public APIs.
- Use scenario-style tests for critical flows (Arrange / Act / Assert).
- Cover both success and failure paths for behavior changes.
- Assert observable outcomes and side effects together (status/result + counters/state/output contract).
- Prefer comparing full objects (`assert_eq!`) over field-by-field assertions when practical.
- Use `assert!` / `assert!(!...)` for boolean checks (instead of `assert_eq!(..., true/false)`).

## Test Determinism

- Keep tests deterministic and parallel-safe.
- Avoid real network calls in tests.
- Avoid mutating process-global state unless strictly required.
- If global state mutation is required, isolate and serialize those tests.

## Tooling Expectations

- If required tools are missing, install them before proceeding (for example: `just`, `rg`, `cargo-nextest`).
- `cargo-nextest` is preferred for speed when available; fallback to `cargo test` is acceptable.

## Documentation Updates

When behavior or API changes:

- Update relevant docs in:
  - `src/normcore-rs/README.md`
  - root `README.md` (if user-facing behavior changes)
  - `formal/` docs if normative behavior/contract changes

## Dependency Changes

If `src/normcore-rs/Cargo.toml` changes:

1. Update `src/normcore-rs/Cargo.lock` in the same change.
2. Re-run full Rust checks (`just check`).

## Safety Constraints

- Do not hardcode secrets or tokens in source, tests, fixtures, or scripts.
- Never use destructive git commands (`git reset --hard`, `git checkout --`) unless explicitly requested.
- Never add or modify logic related to `CODEX_SANDBOX_NETWORK_DISABLED_ENV_VAR` or `CODEX_SANDBOX_ENV_VAR`.
