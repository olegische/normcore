# Formal Models

This directory contains two TLA+ reference models:

- `formal/draft/` — model derived from `context/draft-romanchuk-normative-admissibility-00.txt`
- `formal/implementation/` — model derived from current code and tests in `src/` and `tests/`

Supporting files:

- `formal/draft-vs-implementation.md` — semantic delta between both models
- `formal/draft/chatgpt-feedback-resolution.md` — resolution of external feedback for draft model

## Requirements

- Java (JRE/JDK)
- TLC (`tlc` on `PATH`)

## Run

From repository root.

Run draft model:

```bash
cd formal/draft
# Single worker avoids sandbox port issues
# Use -deadlock to check for deadlocks
tlc -deadlock -workers 1 spec.tla
```

Run implementation model:

```bash
cd formal/implementation
# Single worker avoids sandbox port issues
# Use -deadlock to check for deadlocks
tlc -deadlock -workers 1 spec.tla
```

Note: `formal/implementation/spec.cfg` uses `InitOnlySpec` by default
(fast state-space validation for current classifier-style runtime behavior).
`Spec` (full transition graph) is available in `spec.tla` but is much more expensive.

## Files

Draft model files:

- `formal/draft/spec.tla` — TLA+ model
- `formal/draft/spec.cfg` — TLC config (spec + invariants)
- `formal/draft/property-map.md` — property traceability
- `formal/draft/trace-schema.md` — event/action mapping

Implementation model files:

- `formal/implementation/spec.tla` — TLA+ model
- `formal/implementation/spec.cfg` — TLC config (spec + invariants)
- `formal/implementation/property-map.md` — property traceability
- `formal/implementation/trace-schema.md` — event/action mapping
