import pytest

from normcore.normative.models import GroundSet, KnowledgeNode, License, Modality, Scope, Source, Status


def _node(node_id: str, scope: Scope = Scope.FACTUAL, strength: str = "strong", semantic_id=None) -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        source=Source.OBSERVED,
        status=Status.CONFIRMED,
        confidence=1.0,
        scope=scope,
        strength=strength,
        semantic_id=semantic_id,
    )


def test_knowledge_node_validates_confidence_range():
    with pytest.raises(ValueError):
        KnowledgeNode(
            id="n1",
            source=Source.OBSERVED,
            status=Status.CONFIRMED,
            confidence=1.5,
            scope=Scope.FACTUAL,
            strength="strong",
        )


def test_knowledge_node_validates_strength():
    with pytest.raises(ValueError):
        KnowledgeNode(
            id="n1",
            source=Source.OBSERVED,
            status=Status.CONFIRMED,
            confidence=1.0,
            scope=Scope.FACTUAL,
            strength="invalid",
        )


def test_ground_set_scope_strength():
    ground_set = GroundSet(nodes=[_node("n1", strength="weak"), _node("n2", strength="strong")])
    assert ground_set.get_scope_strength(Scope.FACTUAL) == "strong"


def test_ground_set_resolve_by_id_or_semantic_id():
    node = _node("n1", semantic_id="sem1")
    ground_set = GroundSet(nodes=[node])
    assert ground_set.resolve_ground("n1") == node
    assert ground_set.resolve_ground("sem1") == node


def test_license_permits():
    license = License(permitted_modalities={Modality.ASSERTIVE})
    assert license.permits(Modality.ASSERTIVE)
    assert not license.permits(Modality.CONDITIONAL)
