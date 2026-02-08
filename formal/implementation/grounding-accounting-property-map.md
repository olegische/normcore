# Property Map for FR-NORMCORE-IMPL-0001 (Grounding Accounting Model)

Model status: `PARTIAL` (safety-focused accounting invariants)
Model role: `grounding_accounting`

| Property ID | Type | Statement | Source | Status |
|-------------|------|-----------|--------|--------|
| I-GROUND-UNION-FEASIBLE | invariant | `groundsAccepted` is a feasible unique-union bound of tool and external accepted grounds. | `src/normcore/evaluator.py`, `src/normcore/citations/grounds.py` | REQUIRED |
| I-GROUND-CITED-BOUNDED | invariant | `groundsCited <= groundsAccepted`. | `src/normcore/evaluator.py` | REQUIRED |
| I-EXTERNAL-FORMAT-CONSISTENT | invariant | If external grounds accepted count is `0`, input format is canonical `none`; otherwise format is one of accepted sources. | `src/normcore/citations/grounds.py`, `src/normcore/citations/openai_adapter.py` | REQUIRED |
