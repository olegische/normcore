---- MODULE spec ----
EXTENDS TLC

(*
DERIVATION artifact.
Source authority: context/draft-romanchuk-normative-admissibility-00.txt
Scope: Draft-defined single-statement evaluation semantics.
*)

Modalities == {"ASSERTIVE", "CONDITIONAL", "REFUSAL", "DESCRIPTIVE"}
StrengthValues == {"none", "weak", "strong"}
Statuses ==
    {"ACCEPTABLE", "CONDITIONALLY_ACCEPTABLE", "VIOLATES_NORM",
     "UNSUPPORTED", "ILL_FORMED", "UNDERDETERMINED"}

VARIABLES
    f1Formable,
    f2ContextIndependent,
    f3NoSelfReference,
    modalityDeterminable,
    groundingDeterminable,
    modality,
    conditionsDeclared,
    factualStrength,
    contextualStrength,
    statementStatus

vars ==
    <<f1Formable, f2ContextIndependent, f3NoSelfReference,
      modalityDeterminable, groundingDeterminable, modality,
      conditionsDeclared, factualStrength, contextualStrength, statementStatus>>

GroundSetEmpty(factual, contextual) ==
    factual = "none" /\ contextual = "none"

License(factual, contextual) ==
    IF GroundSetEmpty(factual, contextual)
    THEN {"REFUSAL"}
    ELSE IF factual = "none" /\ contextual # "none"
    THEN {"REFUSAL"}
    ELSE IF factual = "weak"
    THEN {"CONDITIONAL", "REFUSAL"}
    ELSE IF factual = "strong" /\ contextual = "weak"
    THEN {"CONDITIONAL", "REFUSAL"}
    ELSE IF factual = "strong" /\ contextual \in {"none", "strong"}
    THEN {"ASSERTIVE", "CONDITIONAL", "REFUSAL"}
    ELSE {"CONDITIONAL", "REFUSAL"}

EvalStatus(
    f1, f2, f3, modalityKnown, groundingKnown, m, conds, factual, contextual
) ==
    IF ~(f1 /\ f2 /\ f3)
    THEN "ILL_FORMED"
    ELSE IF ~modalityKnown
    THEN "UNDERDETERMINED"
    ELSE IF ~groundingKnown
    THEN "UNDERDETERMINED"
    ELSE IF m = "REFUSAL"
    THEN "ACCEPTABLE"
    ELSE IF m = "ASSERTIVE" /\ ~("ASSERTIVE" \in License(factual, contextual))
    THEN "VIOLATES_NORM"
    ELSE IF m = "CONDITIONAL" /\ conds
    THEN "CONDITIONALLY_ACCEPTABLE"
    ELSE IF m \in {"ASSERTIVE", "CONDITIONAL"} /\ GroundSetEmpty(factual, contextual)
    THEN "UNSUPPORTED"
    ELSE IF m = "DESCRIPTIVE" /\ factual # "none"
    THEN "ACCEPTABLE"
    ELSE IF m = "ASSERTIVE" /\ ("ASSERTIVE" \in License(factual, contextual))
    THEN "ACCEPTABLE"
    ELSE "UNDERDETERMINED"

TypeOK ==
    /\ f1Formable \in BOOLEAN
    /\ f2ContextIndependent \in BOOLEAN
    /\ f3NoSelfReference \in BOOLEAN
    /\ modalityDeterminable \in BOOLEAN
    /\ groundingDeterminable \in BOOLEAN
    /\ modality \in Modalities
    /\ conditionsDeclared \in BOOLEAN
    /\ factualStrength \in StrengthValues
    /\ contextualStrength \in StrengthValues
    /\ statementStatus \in Statuses

Init ==
    /\ f1Formable \in BOOLEAN
    /\ f2ContextIndependent \in BOOLEAN
    /\ f3NoSelfReference \in BOOLEAN
    /\ modalityDeterminable \in BOOLEAN
    /\ groundingDeterminable \in BOOLEAN
    /\ modality \in Modalities
    /\ conditionsDeclared \in BOOLEAN
    /\ factualStrength \in StrengthValues
    /\ contextualStrength \in StrengthValues
    /\ statementStatus =
        EvalStatus(
            f1Formable, f2ContextIndependent, f3NoSelfReference,
            modalityDeterminable, groundingDeterminable,
            modality, conditionsDeclared, factualStrength, contextualStrength
        )
    /\ TypeOK

Next ==
    /\ f1Formable' \in BOOLEAN
    /\ f2ContextIndependent' \in BOOLEAN
    /\ f3NoSelfReference' \in BOOLEAN
    /\ modalityDeterminable' \in BOOLEAN
    /\ groundingDeterminable' \in BOOLEAN
    /\ modality' \in Modalities
    /\ conditionsDeclared' \in BOOLEAN
    /\ factualStrength' \in StrengthValues
    /\ contextualStrength' \in StrengthValues
    /\ statementStatus' =
        EvalStatus(
            f1Formable', f2ContextIndependent', f3NoSelfReference',
            modalityDeterminable', groundingDeterminable',
            modality', conditionsDeclared', factualStrength', contextualStrength'
        )

Spec ==
    Init /\ [][Next]_vars

InvFConditions ==
    ~(f1Formable /\ f2ContextIndependent /\ f3NoSelfReference)
    => statementStatus = "ILL_FORMED"

InvA6 ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality = "REFUSAL"
    => statementStatus = "ACCEPTABLE"

InvA5 ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality = "ASSERTIVE"
    /\ ~("ASSERTIVE" \in License(factualStrength, contextualStrength))
    => statementStatus = "VIOLATES_NORM"

InvA7 ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality = "CONDITIONAL"
    /\ conditionsDeclared
    => statementStatus = "CONDITIONALLY_ACCEPTABLE"

InvA4 ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality \in {"ASSERTIVE", "CONDITIONAL"}
    /\ GroundSetEmpty(factualStrength, contextualStrength)
    /\ ~(modality = "CONDITIONAL" /\ conditionsDeclared)
    /\ ~(modality = "ASSERTIVE" /\ ~("ASSERTIVE" \in License(factualStrength, contextualStrength)))
    => statementStatus = "UNSUPPORTED"

InvContextualWeakening ==
    /\ factualStrength = "strong"
    /\ contextualStrength = "weak"
    => ~("ASSERTIVE" \in License(factualStrength, contextualStrength))

InvGroundingUnknownIsUnderdetermined ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable
    /\ ~groundingDeterminable
    => statementStatus = "UNDERDETERMINED"

InvModalityUnknownIsUnderdetermined ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ ~modalityDeterminable
    => statementStatus = "UNDERDETERMINED"

InvTotalFunction ==
    statementStatus =
        EvalStatus(
            f1Formable, f2ContextIndependent, f3NoSelfReference,
            modalityDeterminable, groundingDeterminable,
            modality, conditionsDeclared, factualStrength, contextualStrength
        )

InvAcceptableAssertiveLicensed ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality = "ASSERTIVE"
    /\ statementStatus = "ACCEPTABLE"
    => "ASSERTIVE" \in License(factualStrength, contextualStrength)

InvA5BeforeA4ForAssertiveEmptyGround ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality = "ASSERTIVE"
    /\ GroundSetEmpty(factualStrength, contextualStrength)
    => statementStatus = "VIOLATES_NORM"

InvDescriptiveUngroundedFallsToUnderdetermined ==
    /\ f1Formable /\ f2ContextIndependent /\ f3NoSelfReference
    /\ modalityDeterminable /\ groundingDeterminable
    /\ modality = "DESCRIPTIVE"
    /\ factualStrength = "none"
    => statementStatus = "UNDERDETERMINED"

=============================================================================
