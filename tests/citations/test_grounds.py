from normcore.citations.grounds import (
    Ground,
    build_links_from_grounds,
    extract_citation_keys,
    grounds_from_tool_call_refs,
    parse_grounds,
)


def test_extract_citation_keys_preserves_order_and_uniqueness():
    text = "First [@toolCall1], again [@toolCall1], then [@DocX]."
    assert extract_citation_keys(text) == ["toolCall1", "DocX"]


def test_parse_grounds_from_dict_payload():
    grounds = parse_grounds([{"citation_key": "DocX", "ground_id": "file_1"}])
    assert len(grounds) == 1
    assert grounds[0].citation_key == "DocX"


def test_build_links_from_grounds_only_for_cited_keys():
    grounds = [
        Ground(citation_key="toolCall1", ground_id="issue_AGENT-8"),
        Ground(citation_key="DocX", ground_id="file_123"),
    ]
    link_set = build_links_from_grounds(
        text="Need action [@toolCall1], nothing else.",
        grounds=grounds,
        statement_id="final_response",
    )
    assert len(link_set.links) == 1
    assert link_set.links[0].ground_id == "issue_AGENT-8"
    assert link_set.links[0].statement_id == "final_response"


def test_grounds_from_tool_call_refs_expands_multiple_grounds():
    grounds = grounds_from_tool_call_refs(
        {
            "call_a": ["g1", "g2"],
            "call_b": ["g3"],
        }
    )
    assert [(g.citation_key, g.ground_id) for g in grounds] == [
        ("call_a", "g1"),
        ("call_a", "g2"),
        ("call_b", "g3"),
    ]
