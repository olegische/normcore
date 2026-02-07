# Property Map for FR-NORMCORE-IMPL-0001

Model status: `PARTIAL` (safety-focused; no liveness obligations encoded in runtime)

| Property ID | Type | Statement | Source | Status |
|-------------|------|-----------|--------|--------|
| I-CORE-PRECHECK-EMPTY | safety | In `core_text` mode with empty output, evaluator returns `UNDERDETERMINED`, no statement results, `licensed=false`, `can_retry=false`. | `src/normcore/evaluator.py` (`_evaluate_core`) | REQUIRED |
| I-CORE-PRECHECK-NO-NORMATIVE | safety | In `core_text` mode with zero extracted statements, evaluator returns `NO_NORMATIVE_CONTENT`, no statement results, `licensed=false`, `can_retry=false`. | `src/normcore/evaluator.py` (`_evaluate_core`) | REQUIRED |
| I-SINGLE-STATEMENT-MODEL | invariant | Evaluated path has exactly one statement result (current extractor behavior). | `src/normcore/normative/statement_extractor.py` | REQUIRED |
| I-REFUSAL-ENTRY-PATH | safety | `assistant_refusal` entry always yields final status `ACCEPTABLE`, `licensed=true`, `can_retry=false`. | `src/normcore/evaluator.py` (`_evaluate_refusal`, `_aggregate`) | REQUIRED |
| I-LINKS-REACHABILITY | invariant | In links mode, effective linked factual strength cannot exceed available factual grounding strength; conservative mode has no linked factual strength. | `src/normcore/normative/license_deriver.py` | REQUIRED |
| I-A6-REFUSAL | safety | `REFUSAL` modality yields statement status `ACCEPTABLE`. | `src/normcore/normative/axiom_checker.py`; `tests/normative/test_axiom_checker.py` | REQUIRED |
| I-A5-ASSERTIVE-LICENSE | safety | Unlicensed `ASSERTIVE` statement yields `VIOLATES_NORM`. | `src/normcore/normative/axiom_checker.py`; `tests/normative/test_axiom_checker.py` | REQUIRED |
| I-A7-CONDITIONAL-ACCEPT | safety | `CONDITIONAL` statement with declared conditions or assertive license yields `CONDITIONALLY_ACCEPTABLE`. | `src/normcore/normative/axiom_checker.py`; `tests/normative/test_axiom_checker.py` | REQUIRED |
| I-A7-CONDITIONAL-UNSUPPORTED | safety | `CONDITIONAL` statement without conditions and without assertive license yields `UNSUPPORTED`. | `src/normcore/normative/axiom_checker.py`; `tests/normative/test_axiom_checker.py` | REQUIRED |
| I-DESCRIPTIVE-FACTUAL | invariant | `DESCRIPTIVE` statement with factual ground is `ACCEPTABLE`, else `UNSUPPORTED`. | `src/normcore/normative/axiom_checker.py`; `tests/normative/test_axiom_checker.py` | REQUIRED |
| I-AGG-STATUS-LICENSE-RETRY | invariant | Final status/`licensed`/`can_retry` in evaluated paths are exact functions of statement statuses via `_aggregate` priority rules. | `src/normcore/evaluator.py` (`_aggregate`); `tests/evaluator/test_evaluator_aggregate.py` | REQUIRED |
| I-LIVE-PROGRESS | liveness | Runtime evaluator defines no liveness/progress obligations. | `src/normcore/evaluator.py`; `src/normcore/normative/*` | OPEN |
