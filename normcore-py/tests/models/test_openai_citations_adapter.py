from openai.types.responses.response_output_text import (
    AnnotationFileCitation,
    AnnotationURLCitation,
)

from normcore.citations import link_set_from_openai_citations, parse_openai_citations
from normcore.models import LinkRole


def test_link_set_from_openai_citations_uses_ground_id():
    citations = [
        AnnotationFileCitation(
            type="file_citation",
            file_id="file_123",
            filename="doc.md",
            index=0,
        )
    ]

    link_set = link_set_from_openai_citations(citations)

    assert len(link_set.links) == 1
    assert link_set.links[0].ground_id == "file_123"
    assert link_set.links[0].role == LinkRole.SUPPORTS


def test_link_set_from_openai_citations_url_falls_back_to_url_ground():
    citations = [
        AnnotationURLCitation(
            type="url_citation",
            url="https://example.com/doc",
            title="Doc",
            start_index=0,
            end_index=10,
        )
    ]

    link_set = link_set_from_openai_citations(citations)

    assert len(link_set.links) == 1
    assert link_set.links[0].ground_id == "https://example.com/doc"


def test_parse_openai_citations_validates_against_openai_schema():
    citations = parse_openai_citations(
        [
            {
                "type": "file_citation",
                "file_id": "file_from_dict",
                "filename": "raw.json",
                "index": 0,
            }
        ]
    )

    assert len(citations) == 1
    assert citations[0].type == "file_citation"


class _DummyCitation:
    def __init__(self, annotation_type: str, **attrs):
        self.type = annotation_type
        for key, value in attrs.items():
            setattr(self, key, value)

    def model_dump(self, mode="json"):
        payload = {"type": self.type}
        payload.update(
            {key: value for key, value in self.__dict__.items() if key not in {"type"}}
        )
        return payload


def test_link_set_skips_citations_with_empty_ids():
    citations = [_DummyCitation("file_citation", file_id="   ")]
    link_set = link_set_from_openai_citations(citations)
    assert link_set.links == []


def test_grounds_from_openai_citations_skips_citations_with_empty_ids():
    from normcore.citations import grounds_from_openai_citations

    citations = [_DummyCitation("url_citation", url=" ")]
    grounds = grounds_from_openai_citations(citations)
    assert grounds == []


def test_link_set_ignores_unknown_annotation_type():
    citations = [_DummyCitation("unknown_annotation", anything="x")]
    link_set = link_set_from_openai_citations(citations)
    assert link_set.links == []


def test_link_set_truncates_large_evidence_payload():
    large_text = "x" * 5000
    citations = [_DummyCitation("file_citation", file_id="file_big", payload=large_text)]
    link_set = link_set_from_openai_citations(citations)
    assert len(link_set.links) == 1
    evidence = link_set.links[0].provenance.evidence_content
    assert evidence.startswith("openai_citation[0]=")
    assert evidence.endswith("...")
