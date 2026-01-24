from dataclasses import dataclass

from evaluator.evaluator import AdmissibilityEvaluator
from evaluator.normative.models import EvaluationStatus


@dataclass
class _Result:
    status: EvaluationStatus
    violated_axiom: str | None = None


def _results(*statuses):
    return [_Result(status=s, violated_axiom=("A5" if s == EvaluationStatus.VIOLATES_NORM else None)) for s in statuses]


def _statement_results(n: int):
    return [object() for _ in range(n)]


def test_aggregate_violates_norm_has_priority():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._aggregate(
        _results(EvaluationStatus.VIOLATES_NORM, EvaluationStatus.ACCEPTABLE),
        _statement_results(2),
        personal_context=None,
        personal_context_scope="unknown",
        personal_context_source="unknown",
    )
    assert result.status == EvaluationStatus.VIOLATES_NORM
    assert result.can_retry is True


def test_aggregate_ill_formed_next_priority():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._aggregate(
        _results(EvaluationStatus.ILL_FORMED, EvaluationStatus.ACCEPTABLE),
        _statement_results(2),
        personal_context=None,
        personal_context_scope="unknown",
        personal_context_source="unknown",
    )
    assert result.status == EvaluationStatus.ILL_FORMED


def test_aggregate_underdetermined():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._aggregate(
        _results(EvaluationStatus.UNDERDETERMINED),
        _statement_results(1),
        personal_context=None,
        personal_context_scope="unknown",
        personal_context_source="unknown",
    )
    assert result.status == EvaluationStatus.UNDERDETERMINED
    assert result.licensed is False


def test_aggregate_unsupported():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._aggregate(
        _results(EvaluationStatus.UNSUPPORTED),
        _statement_results(1),
        personal_context=None,
        personal_context_scope="unknown",
        personal_context_source="unknown",
    )
    assert result.status == EvaluationStatus.UNSUPPORTED
    assert result.can_retry is True


def test_aggregate_conditionally_acceptable():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._aggregate(
        _results(EvaluationStatus.CONDITIONALLY_ACCEPTABLE),
        _statement_results(1),
        personal_context=None,
        personal_context_scope="unknown",
        personal_context_source="unknown",
    )
    assert result.status == EvaluationStatus.CONDITIONALLY_ACCEPTABLE


def test_aggregate_accepts_all_acceptable():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._aggregate(
        _results(EvaluationStatus.ACCEPTABLE, EvaluationStatus.ACCEPTABLE),
        _statement_results(2),
        personal_context=None,
        personal_context_scope="unknown",
        personal_context_source="unknown",
    )
    assert result.status == EvaluationStatus.ACCEPTABLE
    assert result.num_acceptable == 2
