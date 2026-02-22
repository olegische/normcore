from openai.types.responses.response_output_text import AnnotationFileCitation

from normcore.citations import Ground, coerce_grounds_input
from normcore.normative.knowledge_builder import KnowledgeStateBuilder
from normcore.normative.models import KnowledgeNode, Scope, Source, Status


def test_coerce_grounds_accepts_explicit_grounds():
    grounds = coerce_grounds_input(
        grounds=[{"citation_key": "doc1", "ground_id": "file_abc"}],
    )
    assert len(grounds) == 1
    assert grounds[0].citation_key == "doc1"
    assert grounds[0].ground_id == "file_abc"


def test_coerce_grounds_accepts_openai_annotations_payload():
    grounds = coerce_grounds_input(
        grounds=[
            AnnotationFileCitation(
                type="file_citation",
                file_id="file_from_grounds",
                filename="history.txt",
                index=0,
            )
        ],
    )
    assert len(grounds) == 1
    assert grounds[0].citation_key == "file_from_grounds"
    assert grounds[0].ground_id == "file_from_grounds"


def test_coerce_grounds_adds_legacy_openai_citations():
    grounds = coerce_grounds_input(
        grounds=[Ground(citation_key="local", ground_id="g1")],
        legacy_openai_citations=[
            AnnotationFileCitation(
                type="file_citation",
                file_id="file_from_legacy",
                filename="legacy.txt",
                index=0,
            )
        ],
    )
    assert {g.citation_key for g in grounds} == {"local", "file_from_legacy"}


def test_coerce_grounds_invalid_inputs_are_ignored():
    grounds = coerce_grounds_input(
        grounds=[{"ground_id": "missing_key"}],  # invalid ground
        legacy_openai_citations=[{"type": "file_citation"}],  # invalid legacy citation
        legacy_links={"links": []},  # deprecated ignored
    )
    assert grounds == []


def test_materialize_external_ground_nodes_injects_missing_grounds():
    initial = [
        KnowledgeNode(
            id="tool_weather",
            source=Source.OBSERVED,
            status=Status.CONFIRMED,
            confidence=1.0,
            scope=Scope.FACTUAL,
            strength="strong",
            semantic_id="weather_nyc",
        )
    ]
    grounds = [Ground(citation_key="file_hist", ground_id="archive_nyc_weather_2025-02-07")]
    builder = KnowledgeStateBuilder()

    out = builder.materialize_external_grounds(initial, grounds)

    assert len(out) == 2
    assert any(node.id == "archive_nyc_weather_2025-02-07" for node in out)


def test_materialize_external_ground_nodes_skips_existing_ids():
    initial = [
        KnowledgeNode(
            id="archive_nyc_weather_2025-02-07",
            source=Source.OBSERVED,
            status=Status.CONFIRMED,
            confidence=1.0,
            scope=Scope.FACTUAL,
            strength="strong",
            semantic_id="archive_nyc_weather_2025-02-07",
        )
    ]
    grounds = [Ground(citation_key="file_hist", ground_id="archive_nyc_weather_2025-02-07")]
    builder = KnowledgeStateBuilder()

    out = builder.materialize_external_grounds(initial, grounds)

    assert len(out) == 1
