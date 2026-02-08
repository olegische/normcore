from normcore.citations import link_set_from_openai_citations, parse_openai_citations
from normcore.models import LinkRole
from openai.types.responses.response_output_text import AnnotationFileCitation, AnnotationURLCitation


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
