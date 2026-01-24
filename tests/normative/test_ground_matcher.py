from evaluator.normative.ground_matcher import GroundSetMatcher
from evaluator.normative.models import KnowledgeNode, Modality, Scope, Source, Statement, Status


def _node(node_id: str, scope: Scope) -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        source=Source.OBSERVED,
        status=Status.CONFIRMED,
        confidence=1.0,
        scope=scope,
        strength="strong",
    )


def _statement(modality: Modality) -> Statement:
    return Statement(
        id="s1",
        subject="agent",
        predicate="participation",
        raw_text="text",
        modality=modality,
    )


def test_descriptive_only_matches_factual():
    matcher = GroundSetMatcher()
    nodes = [_node("f1", Scope.FACTUAL), _node("c1", Scope.CONTEXTUAL)]
    ground_set = matcher.match(_statement(Modality.DESCRIPTIVE), nodes)
    assert [n.id for n in ground_set.nodes] == ["f1"]


def test_assertive_matches_factual_and_contextual():
    matcher = GroundSetMatcher()
    nodes = [_node("f1", Scope.FACTUAL), _node("c1", Scope.CONTEXTUAL)]
    ground_set = matcher.match(_statement(Modality.ASSERTIVE), nodes)
    assert {n.id for n in ground_set.nodes} == {"f1", "c1"}


def test_refusal_matches_no_grounding():
    matcher = GroundSetMatcher()
    nodes = [_node("f1", Scope.FACTUAL)]
    ground_set = matcher.match(_statement(Modality.REFUSAL), nodes)
    assert ground_set.nodes == []
