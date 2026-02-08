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

    id: str
    scope: str
    source: str
    status: str
    confidence: float
    strength: str
    semantic_id: Optional[str] = None


class StatementEvaluation(BaseModel):
    """
    Per-statement evaluation result (spec: EvaluationResult).
    """

    statement_id: str
    statement: str
    modality: str
    license: set[str]
    status: AdmissibilityStatus
    violated_axiom: Optional[str] = None
    explanation: str = ""
    grounding_trace: list[GroundRef] = Field(default_factory=list)

    subject: Optional[str] = None
    predicate: Optional[str] = None


EvaluationResult = StatementEvaluation


class AdmissibilityJudgment(BaseModel):
    """
    Aggregated judgment for a whole message / speech act.
    """

    status: AdmissibilityStatus
    licensed: bool
    can_retry: bool
    statement_evaluations: list[StatementEvaluation] = Field(default_factory=list)

    feedback_hint: Optional[str] = None
    violated_axioms: list[str] = Field(default_factory=list)
    explanation: str = ""

    num_statements: int = 0
    num_acceptable: int = 0
    personal_context_source: str = "unknown"
    personal_context_scope: str = "unknown"
    personal_context_present: bool = False
    grounds_accepted: int = 0
    grounds_cited: int = 0
