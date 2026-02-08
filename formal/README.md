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

Run implementation grounds-accounting model:

```bash
cd formal/implementation
# Single worker avoids sandbox port issues
# Use -deadlock to check for deadlocks
tlc -deadlock -workers 1 grounding_accounting.tla -config grounding_accounting.cfg
```

Note: implementation configs now use `Spec` by default (full transition graph).
If you need fast init-only validation, switch `SPECIFICATION` to `InitOnlySpec`
in the corresponding `.cfg`.

## Files

Draft model files:

- `formal/draft/spec.tla` — TLA+ model
- `formal/draft/spec.cfg` — TLC config (spec + invariants)
- `formal/draft/property-map.md` — property traceability
- `formal/draft/trace-schema.md` — event/action mapping

Implementation model files (split by concern):

- `formal/implementation/spec.tla` — core decision semantics model
- `formal/implementation/spec.cfg` — TLC config for core decision model
- `formal/implementation/grounding_accounting.tla` — grounds accounting model
- `formal/implementation/grounding_accounting.cfg` — TLC config for grounds accounting model
- `formal/implementation/property-map.md` — property traceability (core decision)
- `formal/implementation/grounding-accounting-property-map.md` — property traceability (grounding accounting)
- `formal/implementation/trace-schema.md` — event/action mapping (core decision)
- `formal/implementation/grounding-accounting-trace-schema.md` — event/action mapping (grounding accounting)
