from normcore.normative.axiom_checker import AxiomChecker
from normcore.normative.models import (
    EvaluationStatus,
    GroundSet,
    KnowledgeNode,
    License,
    Modality,
    Scope,
    Source,
    Statement,
    Status,
)


def _statement(modality: Modality, conditions=None) -> Statement:
    return Statement(
        id="s1",
        subject="agent",
        predicate="participation",
        raw_text="text",
        modality=modality,
        conditions=conditions or [],
    )


def _node(scope: Scope = Scope.FACTUAL, strength: str = "strong") -> KnowledgeNode:
    return KnowledgeNode(
        id="n1",
        source=Source.OBSERVED,
        status=Status.CONFIRMED,
        confidence=1.0,
        scope=scope,
        strength=strength,
    )


def test_refusal_is_always_acceptable():
    checker = AxiomChecker()
    statement = _statement(Modality.REFUSAL)
    result = checker.check(statement, License(set()), GroundSet([]), task_goal="goal")
    assert result.status == EvaluationStatus.ACCEPTABLE


def test_assertive_without_license_violates_a5():
    checker = AxiomChecker()
    statement = _statement(Modality.ASSERTIVE)
    license = License(permitted_modalities={Modality.REFUSAL})
    result = checker.check(statement, license, GroundSet([]), task_goal="goal")
    assert result.status == EvaluationStatus.VIOLATES_NORM
    assert result.violated_axiom == "A5"


def test_conditional_with_assertive_license_is_conditionally_acceptable():
    checker = AxiomChecker()
    statement = _statement(Modality.CONDITIONAL, conditions=["x"])
    license = License(permitted_modalities={Modality.ASSERTIVE, Modality.CONDITIONAL})
    result = checker.check(statement, license, GroundSet([_node()]), task_goal="goal")
    assert result.status == EvaluationStatus.CONDITIONALLY_ACCEPTABLE


def test_conditional_without_conditions_is_unsupported():
    checker = AxiomChecker()
    statement = _statement(Modality.CONDITIONAL, conditions=[])
    license = License(permitted_modalities={Modality.CONDITIONAL})
    result = checker.check(statement, license, GroundSet([_node()]), task_goal="goal")
    assert result.status == EvaluationStatus.UNSUPPORTED
    assert result.violated_axiom == "A7"


def test_a4_triggers_when_no_grounding_after_other_checks():
    checker = AxiomChecker()
    statement = _statement(Modality.ASSERTIVE)
    license = License(permitted_modalities={Modality.ASSERTIVE})
    result = checker.check(statement, license, GroundSet([]), task_goal="goal")
    assert result.status == EvaluationStatus.UNSUPPORTED
    assert result.violated_axiom == "A4"


def test_descriptive_requires_factual_grounding():
    checker = AxiomChecker()
    statement = _statement(Modality.DESCRIPTIVE)
    grounded = checker.check(statement, License(set()), GroundSet([_node()]), task_goal="goal")
    assert grounded.status == EvaluationStatus.ACCEPTABLE
    ungrounded = checker.check(statement, License(set()), GroundSet([]), task_goal="goal")
    assert ungrounded.status == EvaluationStatus.UNSUPPORTED


def test_default_accepts_when_license_permits():
    checker = AxiomChecker()
    statement = _statement(Modality.ASSERTIVE)
    license = License(permitted_modalities={Modality.ASSERTIVE})
    result = checker.check(statement, license, GroundSet([_node()]), task_goal="goal")
    assert result.status == EvaluationStatus.ACCEPTABLE
