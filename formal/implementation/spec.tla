---- MODULE spec ----
EXTENDS Sequences, TLC, Naturals

(*
DERIVATION artifact.
MODEL_STATUS = "PARTIAL"

Source authority:
- src/normcore/evaluator.py
- src/normcore/normative/axiom_checker.py
- src/normcore/normative/license_deriver.py
- tests/evaluator/test_evaluator_core.py
- tests/evaluator/test_evaluator_aggregate.py
- tests/normative/test_axiom_checker.py
- tests/normative/test_license_deriver.py

Goal: exact reflection of CURRENT runtime behavior (not draft intent).
*)

EvaluationModes == {"core_text", "assistant_refusal"}
CorePaths == {"empty_output", "no_normative", "evaluated"}
Modalities == {"ASSERTIVE", "CONDITIONAL", "REFUSAL", "DESCRIPTIVE"}
StrengthValues == {"none", "weak", "strong"}
LicenseModes == {"conservative", "links"}

\* Statuses produced by current AxiomChecker for normal evaluator paths.
GeneratedStatementStatuses ==
    {"ACCEPTABLE", "CONDITIONALLY_ACCEPTABLE", "VIOLATES_NORM", "UNSUPPORTED"}

\* Kept for aggregate function completeness (branches exist in code).
AggregateInputStatuses ==
    GeneratedStatementStatuses \cup {"ILL_FORMED", "UNDERDETERMINED"}

CoreStatuses == AggregateInputStatuses \cup {"NO_NORMATIVE_CONTENT"}

StatementStatusSeqs ==
    {<<>>} \cup {<<s>> : s \in AggregateInputStatuses}

VARIABLES
    evaluationMode,
    path,
    hasAgentOutput,
    hasNormativeContent,
    modality,
    conditionsDeclared,
    licenseMode,
    factualStrength,
    linksFactualStrength,
    statementStatus,
    statementStatuses,
    coreStatus,
    licensed,
    canRetry

vars ==
    <<evaluationMode, path, hasAgentOutput, hasNormativeContent,
      modality, conditionsDeclared, licenseMode, factualStrength,
      linksFactualStrength, statementStatus, statementStatuses,
      coreStatus, licensed, canRetry>>

Contains(seq, value) ==
    \E i \in 1..Len(seq): seq[i] = value

AssertiveLicensed(mode, factual, linksFactual) ==
    IF mode = "conservative"
    THEN factual = "strong"
    ELSE linksFactual = "strong"

ConditionalAcceptable(conds, mode, factual, linksFactual) ==
    AssertiveLicensed(mode, factual, linksFactual) \/ conds

HasFactualGround(factual) ==
    factual # "none"

EvalStatementStatus(m, conds, mode, factual, linksFactual) ==
    IF m = "REFUSAL"
    THEN "ACCEPTABLE"
    ELSE IF m = "ASSERTIVE" /\ ~AssertiveLicensed(mode, factual, linksFactual)
    THEN "VIOLATES_NORM"
    ELSE IF m = "CONDITIONAL" /\ ConditionalAcceptable(conds, mode, factual, linksFactual)
    THEN "CONDITIONALLY_ACCEPTABLE"
    ELSE IF m = "CONDITIONAL" /\ ~ConditionalAcceptable(conds, mode, factual, linksFactual)
    THEN "UNSUPPORTED"
    ELSE IF m \in {"ASSERTIVE", "CONDITIONAL"} /\ ~HasFactualGround(factual)
    THEN "UNSUPPORTED"
    ELSE IF m = "DESCRIPTIVE" /\ HasFactualGround(factual)
    THEN "ACCEPTABLE"
    ELSE IF m = "DESCRIPTIVE" /\ ~HasFactualGround(factual)
    THEN "UNSUPPORTED"
    ELSE IF m = "ASSERTIVE" /\ AssertiveLicensed(mode, factual, linksFactual)
    THEN "ACCEPTABLE"
    ELSE "UNDERDETERMINED"

AggregateStatuses(seqStatuses) ==
    IF Contains(seqStatuses, "VIOLATES_NORM")
    THEN "VIOLATES_NORM"
    ELSE IF Contains(seqStatuses, "ILL_FORMED")
    THEN "ILL_FORMED"
    ELSE IF Contains(seqStatuses, "UNDERDETERMINED")
    THEN "UNDERDETERMINED"
    ELSE IF Contains(seqStatuses, "UNSUPPORTED")
    THEN "UNSUPPORTED"
    ELSE IF Contains(seqStatuses, "CONDITIONALLY_ACCEPTABLE")
    THEN "CONDITIONALLY_ACCEPTABLE"
    ELSE "ACCEPTABLE"

AggregateLicensed(seqStatuses) ==
    IF Contains(seqStatuses, "VIOLATES_NORM")
    THEN FALSE
    ELSE IF Contains(seqStatuses, "ILL_FORMED")
    THEN FALSE
    ELSE IF Contains(seqStatuses, "UNDERDETERMINED")
    THEN FALSE
    ELSE TRUE

AggregateCanRetry(seqStatuses) ==
    IF Contains(seqStatuses, "VIOLATES_NORM")
    THEN TRUE
    ELSE IF Contains(seqStatuses, "ILL_FORMED")
    THEN TRUE
    ELSE IF Contains(seqStatuses, "UNDERDETERMINED")
    THEN FALSE
    ELSE IF Contains(seqStatuses, "UNSUPPORTED")
    THEN TRUE
    ELSE FALSE

\* Reachability constraints for links-mode abstraction:
\* links factual strength must be derivable from available factual grounding.
LinksStrengthFeasible(mode, factual, linksFactual) ==
    IF mode = "conservative"
    THEN linksFactual = "none"
    ELSE IF factual = "none"
    THEN linksFactual = "none"
    ELSE IF factual = "weak"
    THEN linksFactual \in {"none", "weak"}
    ELSE linksFactual \in {"none", "weak", "strong"}

CoreFlowConsistent ==
    IF evaluationMode = "assistant_refusal"
    THEN
        /\ path = "evaluated"
        /\ hasAgentOutput = TRUE
        /\ hasNormativeContent = TRUE
        /\ modality = "REFUSAL"
        /\ conditionsDeclared = FALSE
        /\ statementStatus =
            EvalStatementStatus(
                modality, conditionsDeclared, licenseMode, factualStrength, linksFactualStrength
            )
        /\ statementStatuses = <<statementStatus>>
        /\ coreStatus = AggregateStatuses(statementStatuses)
        /\ licensed = AggregateLicensed(statementStatuses)
        /\ canRetry = AggregateCanRetry(statementStatuses)
    ELSE
        /\ evaluationMode = "core_text"
        /\ IF path = "empty_output"
           THEN
               /\ hasAgentOutput = FALSE
               /\ hasNormativeContent = FALSE
               /\ statementStatuses = <<>>
               /\ coreStatus = "UNDERDETERMINED"
               /\ licensed = FALSE
               /\ canRetry = FALSE
           ELSE IF path = "no_normative"
           THEN
               /\ hasAgentOutput = TRUE
               /\ hasNormativeContent = FALSE
               /\ statementStatuses = <<>>
               /\ coreStatus = "NO_NORMATIVE_CONTENT"
               /\ licensed = FALSE
               /\ canRetry = FALSE
           ELSE
               /\ path = "evaluated"
               /\ hasAgentOutput = TRUE
               /\ hasNormativeContent = TRUE
               /\ statementStatus =
                    EvalStatementStatus(
                        modality, conditionsDeclared, licenseMode, factualStrength, linksFactualStrength
                    )
               /\ statementStatuses = <<statementStatus>>
               /\ coreStatus = AggregateStatuses(statementStatuses)
               /\ licensed = AggregateLicensed(statementStatuses)
               /\ canRetry = AggregateCanRetry(statementStatuses)

TypeOK ==
    /\ evaluationMode \in EvaluationModes
    /\ path \in CorePaths
    /\ hasAgentOutput \in BOOLEAN
    /\ hasNormativeContent \in BOOLEAN
    /\ modality \in Modalities
    /\ conditionsDeclared \in BOOLEAN
    /\ licenseMode \in LicenseModes
    /\ factualStrength \in StrengthValues
    /\ linksFactualStrength \in StrengthValues
    /\ statementStatus \in AggregateInputStatuses
    /\ statementStatuses \in StatementStatusSeqs
    /\ coreStatus \in CoreStatuses
    /\ licensed \in BOOLEAN
    /\ canRetry \in BOOLEAN
    /\ LinksStrengthFeasible(licenseMode, factualStrength, linksFactualStrength)

Init ==
    /\ evaluationMode \in EvaluationModes
    /\ path \in CorePaths
    /\ hasAgentOutput \in BOOLEAN
    /\ hasNormativeContent \in BOOLEAN
    /\ modality \in Modalities
    /\ conditionsDeclared \in BOOLEAN
    /\ licenseMode \in LicenseModes
    /\ factualStrength \in StrengthValues
    /\ linksFactualStrength \in StrengthValues
    /\ statementStatus \in AggregateInputStatuses
    /\ statementStatuses \in StatementStatusSeqs
    /\ coreStatus \in CoreStatuses
    /\ licensed \in BOOLEAN
    /\ canRetry \in BOOLEAN
    /\ TypeOK
    /\ CoreFlowConsistent

Next ==
    /\ evaluationMode' \in EvaluationModes
    /\ path' \in CorePaths
    /\ hasAgentOutput' \in BOOLEAN
    /\ hasNormativeContent' \in BOOLEAN
    /\ modality' \in Modalities
    /\ conditionsDeclared' \in BOOLEAN
    /\ licenseMode' \in LicenseModes
    /\ factualStrength' \in StrengthValues
    /\ linksFactualStrength' \in StrengthValues
    /\ statementStatus' \in AggregateInputStatuses
    /\ statementStatuses' \in StatementStatusSeqs
    /\ coreStatus' \in CoreStatuses
    /\ licensed' \in BOOLEAN
    /\ canRetry' \in BOOLEAN
    /\ TypeOK'
    /\ CoreFlowConsistent'

\* Full transition relation (kept for completeness, expensive and usually unnecessary).
Spec ==
    Init /\ [][Next]_vars

\* Practical profile for this project: evaluator is a pure classifier, so
\* checking all admissible runtime states is sufficient.
InitOnlySpec ==
    Init /\ [][UNCHANGED vars]_vars

\* Exact-flow invariants
InvPrecheckEmptyOutput ==
    /\ evaluationMode = "core_text"
    /\ path = "empty_output"
    => /\ coreStatus = "UNDERDETERMINED"
       /\ statementStatuses = <<>>
       /\ licensed = FALSE
       /\ canRetry = FALSE

InvPrecheckNoNormative ==
    /\ evaluationMode = "core_text"
    /\ path = "no_normative"
    => /\ coreStatus = "NO_NORMATIVE_CONTENT"
       /\ statementStatuses = <<>>
       /\ licensed = FALSE
       /\ canRetry = FALSE

InvEvaluatedSingleStatement ==
    path = "evaluated" => Len(statementStatuses) = 1

InvCoreStatusFromAggregateInEvaluatedPath ==
    /\ path = "evaluated"
    => /\ coreStatus = AggregateStatuses(statementStatuses)
       /\ licensed = AggregateLicensed(statementStatuses)
       /\ canRetry = AggregateCanRetry(statementStatuses)

InvRefusalEntryAlwaysAcceptable ==
    evaluationMode = "assistant_refusal"
    => /\ modality = "REFUSAL"
       /\ coreStatus = "ACCEPTABLE"
       /\ licensed = TRUE
       /\ canRetry = FALSE

InvLinksFeasible ==
    LinksStrengthFeasible(licenseMode, factualStrength, linksFactualStrength)

\* Statement-level logic invariants (evaluated path only)
InvA6 ==
    /\ path = "evaluated"
    /\ modality = "REFUSAL"
    => statementStatus = "ACCEPTABLE"

InvA5 ==
    /\ path = "evaluated"
    /\ modality = "ASSERTIVE"
    /\ ~AssertiveLicensed(licenseMode, factualStrength, linksFactualStrength)
    => statementStatus = "VIOLATES_NORM"

InvA7 ==
    /\ path = "evaluated"
    /\ modality = "CONDITIONAL"
    /\ ConditionalAcceptable(conditionsDeclared, licenseMode, factualStrength, linksFactualStrength)
    => statementStatus = "CONDITIONALLY_ACCEPTABLE"

InvA7Unsupported ==
    /\ path = "evaluated"
    /\ modality = "CONDITIONAL"
    /\ ~ConditionalAcceptable(conditionsDeclared, licenseMode, factualStrength, linksFactualStrength)
    => statementStatus = "UNSUPPORTED"

InvDescriptive ==
    /\ path = "evaluated"
    /\ modality = "DESCRIPTIVE"
    => (
        IF HasFactualGround(factualStrength)
        THEN statementStatus = "ACCEPTABLE"
        ELSE statementStatus = "UNSUPPORTED"
    )

=============================================================================
