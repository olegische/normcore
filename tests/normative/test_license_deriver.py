from datetime import datetime

from normcore.models.links import (
    CreatorType,
    EvidenceType,
    LinkRole,
    LinkSet,
    Provenance,
    StatementGroundLink,
)
from normcore.normative.license_deriver import LicenseDeriver
from normcore.normative.models import GroundSet, KnowledgeNode, Modality, Scope, Source, Status


def _node(node_id: str, scope: Scope = Scope.FACTUAL, strength: str = "strong") -> KnowledgeNode:
    return KnowledgeNode(
        id=node_id,
        source=Source.OBSERVED,
        status=Status.CONFIRMED,
        confidence=1.0,
        scope=scope,
        strength=strength,
        semantic_id=f"sem_{node_id}",
    )


def _link(
    statement_id: str, ground_id: str, role: LinkRole = LinkRole.SUPPORTS
) -> StatementGroundLink:
    return StatementGroundLink(
        statement_id=statement_id,
        ground_id=ground_id,
        role=role,
        provenance=Provenance(
            creator=CreatorType.HUMAN,
            timestamp=datetime.utcnow(),
            evidence_type=EvidenceType.EXPLICIT,
        ),
    )


def test_conservative_license_empty_ground_set():
    deriver = LicenseDeriver()
    license = deriver.derive(GroundSet(nodes=[]))
    assert license.permitted_modalities == {Modality.REFUSAL}


def test_conservative_license_strong_factual():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1", strength="strong")])
    license = deriver.derive(ground_set)
    assert Modality.ASSERTIVE in license.permitted_modalities
    assert Modality.CONDITIONAL in license.permitted_modalities


def test_conservative_license_weak_factual():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1", strength="weak")])
    license = deriver.derive(ground_set)
    assert Modality.ASSERTIVE not in license.permitted_modalities
    assert Modality.CONDITIONAL in license.permitted_modalities


def test_license_with_links_no_supports():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1")])
    links = LinkSet(links=[_link("s1", "n1", role=LinkRole.DISAMBIGUATES)])
    license = deriver.derive(ground_set, links=links)
    assert license.permitted_modalities == {Modality.REFUSAL}


def test_license_with_links_unresolved_supports():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1")])
    links = LinkSet(links=[_link("s1", "missing")])
    license = deriver.derive(ground_set, links=links)
    assert license.permitted_modalities == {Modality.REFUSAL}


def test_license_with_links_strong_supports():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1", strength="strong")])
    links = LinkSet(links=[_link("s1", "n1")])
    license = deriver.derive(ground_set, links=links)
    assert Modality.ASSERTIVE in license.permitted_modalities


def test_license_with_links_weak_supports():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1", strength="weak")])
    links = LinkSet(links=[_link("s1", "n1")])
    license = deriver.derive(ground_set, links=links)
    assert Modality.ASSERTIVE not in license.permitted_modalities


def test_derive_with_trace_includes_mode_and_nodes():
    deriver = LicenseDeriver()
    ground_set = GroundSet(nodes=[_node("n1")])
    license, trace = deriver.derive_with_trace(ground_set)
    assert trace["mode"] == "conservative"
    assert trace["ground_set_size"] == 1
    assert trace["nodes"][0]["id"] == "n1"
    assert Modality.ASSERTIVE in license.permitted_modalities
