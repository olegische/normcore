from normcore.evaluator import AdmissibilityEvaluator
from normcore.normative.models import EvaluationStatus, License, Modality, Statement, StatementValidationResult, ValidationResult
from normcore.normative.models import GroundSet, KnowledgeNode, Scope, Source, Status


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
