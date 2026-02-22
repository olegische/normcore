---- MODULE grounding_accounting ----
EXTENDS TLC, Naturals, Sequences

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

TraceOps == {"GroundingAccountingStep"}

TraceArgsSet ==
    [toolGroundsAccepted: GroundCountValues,
     externalGroundsAccepted: GroundCountValues,
     externalGroundInputFormat: ExternalGroundInputFormats]

TraceExpectSet ==
    [groundsAccepted: GroundCountValues, groundsCited: GroundCountValues]

TraceEventSet ==
    [op: TraceOps, args: TraceArgsSet, expect: TraceExpectSet]

VARIABLES
    toolGroundsAccepted,
    externalGroundsAccepted,
    groundsAccepted,
    groundsCited,
    externalGroundInputFormat,
    log

vars ==
    <<toolGroundsAccepted, externalGroundsAccepted,
      groundsAccepted, groundsCited, externalGroundInputFormat, log>>

BuildTraceEvent(toolCount, externalCount, accepted, cited, inputFormat) ==
    [op |-> "GroundingAccountingStep",
     args |-> [toolGroundsAccepted |-> toolCount,
               externalGroundsAccepted |-> externalCount,
               externalGroundInputFormat |-> inputFormat],
     expect |-> [groundsAccepted |-> accepted, groundsCited |-> cited]]

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
    /\ log \in Seq(TraceEventSet)
    /\ Len(log) <= 1
    /\ UnionCountFeasible(toolGroundsAccepted, externalGroundsAccepted, groundsAccepted)
    /\ groundsCited <= groundsAccepted
    /\ ExternalGroundInputFeasible(externalGroundsAccepted, externalGroundInputFormat)

Init ==
    /\ toolGroundsAccepted \in GroundCountValues
    /\ externalGroundsAccepted \in GroundCountValues
    /\ groundsAccepted \in GroundCountValues
    /\ groundsCited \in GroundCountValues
    /\ externalGroundInputFormat \in ExternalGroundInputFormats
    /\ log = <<>>
    /\ TypeOK

Next ==
    /\ Len(log) = 0
    /\ toolGroundsAccepted' \in GroundCountValues
    /\ externalGroundsAccepted' \in GroundCountValues
    /\ groundsAccepted' \in GroundCountValues
    /\ groundsCited' \in GroundCountValues
    /\ externalGroundInputFormat' \in ExternalGroundInputFormats
    /\ log' = Append(log, BuildTraceEvent(toolGroundsAccepted', externalGroundsAccepted', groundsAccepted', groundsCited', externalGroundInputFormat'))
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
