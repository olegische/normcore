# Property Map for FR-NORMCORE-DRAFT-0001

Model status: `PARTIAL` (no liveness obligations are explicit in source draft)

| Property ID | Type | Statement | Source | Status |
|-------------|------|-----------|--------|--------|
| D-F1F2F3-ILL-FORMED | invariant | If any of F1/F2/F3 is violated, status is `ILL_FORMED`. | Draft §4.2, §9.1 step 1 | REQUIRED |
| D-A6-REFUSAL | safety | `REFUSAL` modality is always `ACCEPTABLE`. | Draft §7.2, §7.5 step 1 | REQUIRED |
| D-A5-ASSERTIVE-LICENSE | safety | Unlicensed `ASSERTIVE` claim is `VIOLATES_NORM`. | Draft §7.1, §7.5 step 2 | REQUIRED |
| D-A7-CONDITIONAL-WITH-CONDS | safety | `CONDITIONAL` with declared conditions is `CONDITIONALLY_ACCEPTABLE`. | Draft §7.3, §7.5 step 3 | REQUIRED |
| D-A4-NORMATIVE-EMPTY-GROUND | safety | Normative claim with empty GroundSet is `UNSUPPORTED`. | Draft §7.4, §7.5 step 4 | REQUIRED |
| D-LICENSE-TABLE-CONTEXTUAL-WEAK | invariant | Strong factual + weak contextual grounding downgrades assertive license. | Draft §6.5 Table 5 | REQUIRED |
| D-UNDERDETERMINED-MODALITY | safety | If modality cannot be determined, result is `UNDERDETERMINED`. | Draft §9.1 step 2 | REQUIRED |
| D-UNDERDETERMINED-GROUNDING | safety | If grounding assessment is incomplete/ambiguous, result is `UNDERDETERMINED`. | Draft §9.1 step 3 | REQUIRED |
| D-TOTAL-FUNCTION | invariant | `EvalStatus` is total for the modeled domain and always returns a status in `Statuses`. | Draft §9.1 + deterministic algorithm form | REQUIRED |
| D-ACCEPTABLE-ASSERTIVE-IMPLIES-LICENSED | invariant | `ASSERTIVE` with status `ACCEPTABLE` implies `ASSERTIVE ∈ License`. | Draft §7.1 + §9.1 branching | REQUIRED |
| D-A5-PRECEDES-A4-ASSERTIVE-EMPTY | invariant | For `ASSERTIVE` with empty ground, A5 branch is selected before A4 (`VIOLATES_NORM`). | Draft §7.5 axiom order | REQUIRED |
| D-DESCRIPTIVE-UNGROUNDED-FALLBACK | safety | `DESCRIPTIVE` with no factual grounding falls to algorithm fallback `UNDERDETERMINED`. | Draft §9.1 branch set + fallback | REQUIRED |
| D-DETERMINISM | invariant | Same input state yields same evaluation result. | Draft §9.2 | REQUIRED |
| D-LIVE-PROGRESS | liveness | No progress/fairness obligation is explicitly normative in the draft text. | Draft §§7–9 | OPEN |
