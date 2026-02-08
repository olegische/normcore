---- MODULE spec ----
EXTENDS Sequences, TLC, Naturals

(*
DERIVATION artifact.
MODEL_STATUS = "PARTIAL"
MODEL_ROLE = "core_decision"

Source authority:
- src/normcore/evaluator.py
- src/normcore/normative/axiom_checker.py
- src/normcore/normative/license_deriver.py
- tests/evaluator/test_evaluator_core.py
- tests/evaluator/test_evaluator_aggregate.py
- tests/normative/test_axiom_checker.py
- tests/normative/test_license_deriver.py

This model captures only decision semantics.
Ground accounting/provenance is modeled separately in
`formal/implementation/grounding_accounting.tla`.
*)

EvaluationModes == {"core_text", "assistant_refusal"}
CorePaths == {"empty_output", "no_normative", "evaluated"}
Modalities == {"ASSERTIVE", "CONDITIONAL", "REFUSAL", "DESCRIPTIVE"}
StrengthValues == {"none", "weak", "strong"}
LicenseModes == {"links"}

GeneratedStatementStatuses ==
    {"ACCEPTABLE", "CONDITIONALLY_ACCEPTABLE", "VIOLATES_NORM", "UNSUPPORTED"}

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
    /\ mode = "links"
    /\ linksFactual = "strong"

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

\* In core model, linksFactualStrength is an abstract effective value.
LinksStrengthFeasible(mode, m, factual, linksFactual) ==
    mode = "links" /\
    IF m = "REFUSAL"
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
        /\ licenseMode = "links"
        /\ factualStrength = "none"
        /\ linksFactualStrength = "none"
        /\ statementStatus = "ACCEPTABLE"
        /\ statementStatuses = <<statementStatus>>
        /\ coreStatus = "ACCEPTABLE"
        /\ licensed = TRUE
        /\ canRetry = FALSE
    ELSE
        /\ evaluationMode = "core_text"
        /\ IF path = "empty_output"
           THEN
               /\ modality = "DESCRIPTIVE"
               /\ conditionsDeclared = FALSE
               /\ licenseMode = "links"
               /\ factualStrength = "none"
               /\ linksFactualStrength = "none"
               /\ statementStatus = "UNDERDETERMINED"
               /\ hasAgentOutput = FALSE
               /\ hasNormativeContent = FALSE
               /\ statementStatuses = <<>>
               /\ coreStatus = "UNDERDETERMINED"
               /\ licensed = FALSE
               /\ canRetry = FALSE
           ELSE IF path = "no_normative"
           THEN
               /\ modality = "DESCRIPTIVE"
               /\ conditionsDeclared = FALSE
               /\ licenseMode = "links"
               /\ factualStrength = "none"
               /\ linksFactualStrength = "none"
               /\ statementStatus = "UNDERDETERMINED"
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
    /\ LinksStrengthFeasible(licenseMode, modality, factualStrength, linksFactualStrength)

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

Spec ==
    Init /\ [][Next]_vars

InitOnlySpec ==
    Init /\ [][UNCHANGED vars]_vars

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
    LinksStrengthFeasible(licenseMode, modality, factualStrength, linksFactualStrength)

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
