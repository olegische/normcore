from openai.types.responses.response_output_text import AnnotationFileCitation

from normcore.citations.coerce import coerce_links_input
from normcore.models.links import LinkRole, LinkSet


def _linkset_dict(ground_id: str = "g1") -> dict:
    return {
        "links": [
            {
                "statement_id": "s1",
                "ground_id": ground_id,
                "role": "supports",
                "provenance": {
                    "creator": "human",
                    "evidence_type": "explicit",
                },
            }
        ]
    }


def test_coerce_returns_same_linkset_instance():
    links = LinkSet.model_validate(_linkset_dict("explicit_ground"))
    out = coerce_links_input(links=links, openai_citations=None)
    assert out is links


def test_coerce_validates_linkset_dict():
    out = coerce_links_input(links=_linkset_dict("dict_ground"), openai_citations=None)
    assert isinstance(out, LinkSet)
    assert out.links[0].ground_id == "dict_ground"
    assert out.links[0].role == LinkRole.SUPPORTS


def test_coerce_invalid_linkset_dict_returns_none():
    out = coerce_links_input(links={"links": [{}]}, openai_citations=None)
    assert out is None


def test_coerce_empty_links_list_returns_none():
    out = coerce_links_input(links=[], openai_citations=None)
    assert out is None


def test_coerce_links_list_dict_payload_as_openai_citations():
    out = coerce_links_input(
        links=[
            {
                "type": "file_citation",
                "file_id": "file_from_list_dict",
                "filename": "evidence.txt",
                "index": 0,
            }
        ],
        openai_citations=None,
    )
    assert isinstance(out, LinkSet)
    assert out.links[0].ground_id == "file_from_list_dict"


def test_coerce_links_list_typed_payload_as_openai_citations():
    out = coerce_links_input(
        links=[
            AnnotationFileCitation(
                type="file_citation",
                file_id="file_from_typed_list",
                filename="evidence.txt",
                index=0,
            )
        ],
        openai_citations=None,
    )
    assert isinstance(out, LinkSet)
    assert out.links[0].ground_id == "file_from_typed_list"


def test_coerce_invalid_links_list_returns_none():
    out = coerce_links_input(links=[{"type": "file_citation"}], openai_citations=None)
    assert out is None


def test_coerce_unsupported_links_type_returns_none():
    out = coerce_links_input(links="unsupported", openai_citations=None)  # type: ignore[arg-type]
    assert out is None


def test_coerce_none_inputs_returns_none():
    out = coerce_links_input(links=None, openai_citations=None)
    assert out is None


def test_coerce_openai_citations_when_links_absent():
    out = coerce_links_input(
        links=None,
        openai_citations=[
            AnnotationFileCitation(
                type="file_citation",
                file_id="file_from_openai_citations",
                filename="evidence.txt",
                index=0,
            )
        ],
    )
    assert isinstance(out, LinkSet)
    assert out.links[0].ground_id == "file_from_openai_citations"


def test_coerce_invalid_openai_citations_returns_none():
    out = coerce_links_input(
        links=None,
        openai_citations=[{"type": "file_citation"}],  # type: ignore[list-item]
    )
    assert out is None


def test_coerce_prioritizes_links_over_openai_citations():
    links = LinkSet.model_validate(_linkset_dict("priority_ground"))
    out = coerce_links_input(
        links=links,
        openai_citations=[
            AnnotationFileCitation(
                type="file_citation",
                file_id="should_not_be_used",
                filename="ignored.txt",
                index=0,
            )
        ],
    )
    assert out is links
