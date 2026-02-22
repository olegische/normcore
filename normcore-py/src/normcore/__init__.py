"""
Public API for the NormCore package.
"""

from .evaluator import evaluate
from .models import (
    AdmissibilityJudgment,
    AdmissibilityStatus,
    GroundRef,
    StatementEvaluation,
)

__all__ = [
    "evaluate",
    "AdmissibilityJudgment",
    "AdmissibilityStatus",
    "GroundRef",
    "StatementEvaluation",
]
