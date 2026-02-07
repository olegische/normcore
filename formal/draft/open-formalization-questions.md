# Open Formalization Questions for FR-NORMCORE-DRAFT-0001

| ID | Question | Why It Matters | Status |
|----|----------|----------------|--------|
| D-OQ-001 | Should ungrounded `DESCRIPTIVE` end as `UNDERDETERMINED` (fallback) or `UNSUPPORTED`? | Draft algorithm explicitly accepts grounded descriptive claims but does not assign a dedicated non-grounded descriptive terminal branch before fallback. | OPEN |
| D-OQ-002 | What exact threshold value should be used for STRONG vs WEAK in reference model runs? | Draft gives threshold as illustrative and allows implementation variation; TLC models need concrete finite assumptions when binding confidence to strength. | OPEN |
| D-OQ-003 | Are modality-priority extensions (for example personalization-conditional override) conformant extensions or profile deviations? | Draft defines fixed priority including GOAL-CONDITIONAL override only. | OPEN |
| D-OQ-004 | Should `CONTEXTUAL = none` be treated as epistemically equivalent to `CONTEXTUAL = weak` for assertive licensing? | Draft Table 5 allows assertive license for `(FACTUAL strong, CONTEXTUAL none)` but forbids it for `(FACTUAL strong, CONTEXTUAL weak)`, which can be read as a policy asymmetry. | OPEN |
| D-OQ-005 | Should A7 include explicit `CONDITIONAL ∈ License` guard in the normative algorithm text? | Current algorithm grants `CONDITIONALLY_ACCEPTABLE` on declared conditions before explicit grounding emptiness check; this may be interpreted as broader than license-bounded admissibility. | OPEN |
