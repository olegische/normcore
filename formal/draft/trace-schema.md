# Trace Schema for FR-NORMCORE-DRAFT-0001

| Event | Actor | Inputs | Preconditions | Observable Outcome | TLA+ Action |
|-------|-------|--------|---------------|--------------------|-------------|
| ValidateStructure | Evaluator | Statement structure fields | Statement present | F1/F2/F3 pass or `ILL_FORMED` | `EvalStatus` |
| DetermineModality | Modality layer | Statement text | Structure valid | Modality selected or `UNDERDETERMINED` | `EvalStatus` |
| DeriveGroundingLicense | Grounding layer | GroundSet (factual/contextual strengths) | Modality determined | License set derived or `UNDERDETERMINED` | `License`, `EvalStatus` |
| ApplyA6 | Axiom layer | Modality | Modality=`REFUSAL` | `ACCEPTABLE` | `EvalStatus` |
| ApplyA5 | Axiom layer | Modality + License | Modality=`ASSERTIVE` and assertive disallowed | `VIOLATES_NORM` | `EvalStatus` |
| ApplyA7 | Axiom layer | Modality + conditions flag | Modality=`CONDITIONAL` and conditions declared | `CONDITIONALLY_ACCEPTABLE` | `EvalStatus` |
| ApplyA4 | Axiom layer | Modality + GroundSet emptiness | Normative modality and empty GroundSet | `UNSUPPORTED` | `EvalStatus` |
| FinalizeOutcome | Evaluator | Branch outputs | All branches checked | Final statement status | `statementStatus` |
