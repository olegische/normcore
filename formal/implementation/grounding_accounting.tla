---- MODULE grounding_accounting ----
EXTENDS TLC, Naturals

(*
DERIVATION artifact.
MODEL_STATUS = "PARTIAL"
MODEL_ROLE = "grounding_accounting"

Source authority:
- src/normcore/evaluator.py
- src/normcore/citations/grounds.py
- src/normcore/citations/openai_adapter.py
- src/normcore/normative/knowledge_builder.py
- tests/evaluator/test_evaluator_grounds_input.py

This model captures only accepted/cited ground counters and external
input format consistency. Decision semantics is modeled separately in
`formal/implementation/spec.tla`.
*)

GroundCountValues == 0..4
ExternalGroundInputFormats ==
    {"none", "ground_records", "openai_annotations", "legacy_openai_citations", "invalid_ignored"}

VARIABLES
    toolGroundsAccepted,
    externalGroundsAccepted,
    groundsAccepted,
    groundsCited,
    externalGroundInputFormat

vars ==
    <<toolGroundsAccepted, externalGroundsAccepted,
      groundsAccepted, groundsCited, externalGroundInputFormat>>

UnionCountFeasible(toolCount, externalCount, unionCount) ==
    /\ unionCount >= toolCount
    /\ unionCount >= externalCount
    /\ unionCount <= toolCount + externalCount

ExternalGroundInputFeasible(externalCount, inputFormat) ==
    IF externalCount = 0
    THEN inputFormat = "none"
    ELSE inputFormat \in {"ground_records", "openai_annotations", "legacy_openai_citations"}

TypeOK ==
    /\ toolGroundsAccepted \in GroundCountValues
    /\ externalGroundsAccepted \in GroundCountValues
    /\ groundsAccepted \in GroundCountValues
    /\ groundsCited \in GroundCountValues
    /\ externalGroundInputFormat \in ExternalGroundInputFormats
    /\ UnionCountFeasible(toolGroundsAccepted, externalGroundsAccepted, groundsAccepted)
    /\ groundsCited <= groundsAccepted
    /\ ExternalGroundInputFeasible(externalGroundsAccepted, externalGroundInputFormat)

Init ==
    /\ toolGroundsAccepted \in GroundCountValues
    /\ externalGroundsAccepted \in GroundCountValues
    /\ groundsAccepted \in GroundCountValues
    /\ groundsCited \in GroundCountValues
    /\ externalGroundInputFormat \in ExternalGroundInputFormats
    /\ TypeOK

Next ==
    /\ toolGroundsAccepted' \in GroundCountValues
    /\ externalGroundsAccepted' \in GroundCountValues
    /\ groundsAccepted' \in GroundCountValues
    /\ groundsCited' \in GroundCountValues
    /\ externalGroundInputFormat' \in ExternalGroundInputFormats
    /\ TypeOK'

Spec ==
    Init /\ [][Next]_vars

InitOnlySpec ==
    Init /\ [][UNCHANGED vars]_vars

InvUnionConsistent ==
    UnionCountFeasible(toolGroundsAccepted, externalGroundsAccepted, groundsAccepted)

InvCitedBounded ==
    groundsCited <= groundsAccepted

InvExternalInputConsistent ==
    ExternalGroundInputFeasible(externalGroundsAccepted, externalGroundInputFormat)

InvZeroExternalImpliesNone ==
    externalGroundsAccepted = 0 => externalGroundInputFormat = "none"

=============================================================================
