"""
Public models for the normative admissibility evaluator.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AdmissibilityStatus(str, Enum):
    """
    Aggregated admissibility status for a speech act (and per-statement status).
    """

    ACCEPTABLE = "acceptable"
    CONDITIONALLY_ACCEPTABLE = "conditionally_acceptable"
    VIOLATES_NORM = "violates_norm"
    UNSUPPORTED = "unsupported"
    ILL_FORMED = "ill_formed"
    UNDERDETERMINED = "underdetermined"
    NO_NORMATIVE_CONTENT = "no_normative_content"


class GroundRef(BaseModel):
    """
    A single admitted knowledge atom included in the grounding trace.
    """

    id: str = Field(description="Internal knowledge-node identifier used in grounding trace.")
    scope: str = Field(description="Ground scope label (for example factual).")
    source: str = Field(description="Ground source label (for example observed).")
    status: str = Field(description="Ground node status label (for example confirmed).")
    confidence: float = Field(description="Confidence score attached to the ground node.")
    strength: str = Field(description="Strength label used by licensing logic.")
    semantic_id: Optional[str] = Field(
        default=None,
        description="Optional semantic/external identifier used for link resolution.",
    )


class StatementEvaluation(BaseModel):
    """
    Per-statement evaluation result (spec: EvaluationResult).
    """

    statement_id: str = Field(description="Stable statement identifier (for example final_response).")
    statement: str = Field(description="Statement text that was evaluated.")
    modality: str = Field(description="Detected modality for the statement.")
    license: set[str] = Field(description="Modalities permitted by current grounding.")
    status: AdmissibilityStatus = Field(description="Per-statement admissibility status.")
    violated_axiom: Optional[str] = Field(
        default=None,
        description="Violated axiom identifier when status indicates a violation.",
    )
    explanation: str = Field(
        default="",
        description="Human-readable reason for the per-statement verdict.",
    )
    grounding_trace: list[GroundRef] = Field(
        default_factory=list,
        description="Ground nodes considered for this statement.",
    )

    subject: Optional[str] = Field(
        default=None,
        description="Normalized statement subject used in internal statement model.",
    )
    predicate: Optional[str] = Field(
        default=None,
        description="Normalized statement predicate used in internal statement model.",
    )


EvaluationResult = StatementEvaluation


class AdmissibilityJudgment(BaseModel):
    """
    Aggregated judgment for a whole message / speech act.
    """

    status: AdmissibilityStatus = Field(description="Final admissibility status for whole response.")
    licensed: bool = Field(
        description="Whether grounding permitted the selected normative form(s)."
    )
    can_retry: bool = Field(description="Whether reformulation and retry are recommended.")
    statement_evaluations: list[StatementEvaluation] = Field(
        default_factory=list,
        description="Per-statement evaluation traces used to build the final judgment.",
    )

    feedback_hint: Optional[str] = Field(
        default=None,
        description="Optional retry guidance for the caller/agent.",
    )
    violated_axioms: list[str] = Field(
        default_factory=list,
        description="Aggregate list of violated axiom identifiers.",
    )
    explanation: str = Field(
        default="",
        description="Human-readable explanation of the final verdict.",
    )

    num_statements: int = Field(default=0, description="Total number of evaluated statements.")
    num_acceptable: int = Field(
        default=0,
        description="Count of statements with acceptable or conditionally acceptable outcomes.",
    )
    grounds_accepted: int = Field(
        default=0,
        description="Number of grounds admitted into the evaluation evidence pool.",
    )
    grounds_cited: int = Field(
        default=0,
        description="Number of admitted grounds actually cited in assistant text.",
    )
