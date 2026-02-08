# Trace Schema for FR-NORMCORE-IMPL-0001 (Core Decision Model)

| Event | Actor | Inputs | Preconditions | Observable Outcome | TLA+ Action |
|-------|-------|--------|---------------|--------------------|-------------|
| EvaluateEntry | `AdmissibilityEvaluator.evaluate` | `agent_message`, `trajectory`, optional `grounds` | Message validates against OpenAI schema | Entry mode selected: `core_text` or `assistant_refusal` | `evaluationMode` |
| RefusalEntryPath | Evaluator (`_evaluate_refusal`) | Refusal text + knowledge nodes + optional links | Assistant content is refusal-only | One refusal statement evaluated and aggregated | `CoreFlowConsistent` (assistant_refusal branch) |
| CorePrecheckEmptyOutput | Evaluator (`_evaluate_core`) | `agent_output` | Empty output string | Final status `UNDERDETERMINED`, no statement statuses | `CoreFlowConsistent` (`path="empty_output"`) |
| CorePrecheckNoNormative | Evaluator (`_evaluate_core`) | extracted statements | Extractor returns empty list | Final status `NO_NORMATIVE_CONTENT`, no statement statuses | `CoreFlowConsistent` (`path="no_normative"`) |
| CoreEvaluateSingleStatement | Evaluator core pipeline | one extracted statement + derived grounds + optional links | Non-empty output and normative content present | Single statement status computed and aggregated | `CoreFlowConsistent` (`path="evaluated"`) |
| DeriveLicenseLinks | `LicenseDeriver` | ground set + links | `licenseMode="links"` | License from resolved factual `SUPPORTS` links; model tracks this as a binary assertive-eligible support predicate | `AssertiveLicensed`, `SupportsFeasible` |
| ApplyA6 | `AxiomChecker` | modality + license + grounds | modality is `REFUSAL` | Statement status `ACCEPTABLE` | `EvalStatementStatus` |
| ApplyA5 | `AxiomChecker` | modality + license | modality is `ASSERTIVE` and assertive license absent | Statement status `VIOLATES_NORM` | `EvalStatementStatus` |
| ApplyA7 | `AxiomChecker` | modality + conditions + license | modality is `CONDITIONAL` | `CONDITIONALLY_ACCEPTABLE` if assertive license exists or conditions declared; else `UNSUPPORTED` | `EvalStatementStatus` |
| EvaluateDescriptive | `AxiomChecker` | modality + ground set | modality is `DESCRIPTIVE` | `ACCEPTABLE` with factual ground, else `UNSUPPORTED` | `EvalStatementStatus` |
| AggregateOutcome | Evaluator (`_aggregate`) | statement status sequence | Evaluated path only | Final `status`, `licensed`, `can_retry` via lexicographic branch order | `AggregateStatuses`, `AggregateLicensed`, `AggregateCanRetry` |
