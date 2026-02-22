from types import SimpleNamespace

from normcore.evaluator import AdmissibilityEvaluator
from normcore.normative.models import (
    AxiomCheckResult,
    EvaluationStatus,
    GroundSet,
    KnowledgeNode,
    License,
    Modality,
    Scope,
    Source,
    Statement,
    StatementValidationResult,
    Status,
    ValidationResult,
)


def test_evaluate_core_empty_agent_output():
    evaluator = AdmissibilityEvaluator()
    result = evaluator._evaluate_core(
        agent_output="",
        knowledge_nodes=[],
        links=None,
    )
    assert result.status == EvaluationStatus.UNDERDETERMINED
    assert result.licensed is False


def test_evaluate_core_no_normative_statements_returns_no_normative_content():
    evaluator = AdmissibilityEvaluator()

    class _Extractor:
        def extract(self, text):
            return []

    evaluator.extractor = _Extractor()
    result = evaluator._evaluate_core(
        agent_output="hello",
        knowledge_nodes=[],
        links=None,
    )
    assert result.status == EvaluationStatus.NO_NORMATIVE_CONTENT


def test_to_judgment_maps_status_and_statement_data():
    evaluator = AdmissibilityEvaluator()
    node = KnowledgeNode(
        id="n1",
        source=Source.OBSERVED,
        status=Status.CONFIRMED,
        confidence=1.0,
        scope=Scope.FACTUAL,
        strength="strong",
    )
    statement = Statement(
        id="s1",
        subject="agent",
        predicate="participation",
        raw_text="text",
        modality=Modality.ASSERTIVE,
    )
    stmt_result = StatementValidationResult(
        statement=statement,
        status=EvaluationStatus.ACCEPTABLE,
        license=License(permitted_modalities={Modality.ASSERTIVE}),
        ground_set=GroundSet(nodes=[node]),
        violated_axiom=None,
        explanation="ok",
    )
    validation = ValidationResult(
        status=EvaluationStatus.ACCEPTABLE,
        licensed=True,
        can_retry=False,
        statement_results=[stmt_result],
        explanation="ok",
        num_statements=1,
        num_acceptable=1,
        grounds_accepted=3,
        grounds_cited=2,
    )
    judgment = evaluator._to_judgment(validation)
    assert judgment.status.value == "acceptable"
    assert judgment.statement_evaluations[0].statement_id == "s1"
    assert judgment.grounds_accepted == 3
    assert judgment.grounds_cited == 2


def test_aggregate_mixed_conditional_and_acceptable():
    evaluator = AdmissibilityEvaluator()
    axiom_results = [
        AxiomCheckResult(status=EvaluationStatus.CONDITIONALLY_ACCEPTABLE),
        AxiomCheckResult(status=EvaluationStatus.ACCEPTABLE),
    ]
    statement = Statement(
        id="s1",
        subject="agent",
        predicate="participation",
        raw_text="text",
        modality=Modality.ASSERTIVE,
    )
    stmt_results = [
        StatementValidationResult(
            statement=statement,
            status=EvaluationStatus.CONDITIONALLY_ACCEPTABLE,
            license=License(permitted_modalities={Modality.CONDITIONAL}),
            ground_set=GroundSet(nodes=[]),
        ),
        StatementValidationResult(
            statement=statement,
            status=EvaluationStatus.ACCEPTABLE,
            license=License(permitted_modalities={Modality.ASSERTIVE}),
            ground_set=GroundSet(nodes=[]),
        ),
    ]

    result = evaluator._aggregate(axiom_results, stmt_results)
    assert result.status == EvaluationStatus.CONDITIONALLY_ACCEPTABLE
    assert result.explanation == "Mix of conditional and acceptable statements"


def test_to_judgment_falls_back_on_unknown_status_value():
    fake_status = SimpleNamespace(value="not_a_real_status")
    fake_stmt = SimpleNamespace(
        statement=SimpleNamespace(
            id="s1",
            raw_text="text",
            modality=None,
            subject="agent",
            predicate="participation",
        ),
        license=SimpleNamespace(permitted_modalities=set()),
        status=fake_status,
        violated_axiom=None,
        explanation="fallback",
        ground_set=SimpleNamespace(nodes=[]),
    )
    fake_validation = SimpleNamespace(
        status=fake_status,
        licensed=False,
        can_retry=False,
        statement_results=[fake_stmt],
        feedback_hint=None,
        explanation="fallback",
        num_statements=1,
        num_acceptable=0,
        grounds_accepted=0,
        grounds_cited=0,
    )

    judgment = AdmissibilityEvaluator._to_judgment(fake_validation)
    assert judgment.status.value == "underdetermined"
    assert judgment.statement_evaluations[0].status.value == "underdetermined"
