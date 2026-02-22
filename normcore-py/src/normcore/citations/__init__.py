"""Citation subsystem for parsing and adapting evidence references."""

from .coerce import coerce_links_input
from .grounds import (
    Ground,
    build_links_from_grounds,
    coerce_grounds_input,
    extract_citation_keys,
    grounds_from_tool_call_refs,
    parse_grounds,
)
from .openai_adapter import (
    OpenAICitation,
    grounds_from_openai_citations,
    link_set_from_openai_citations,
    parse_openai_citations,
)

__all__ = [
    "Ground",
    "OpenAICitation",
    "build_links_from_grounds",
    "coerce_grounds_input",
    "coerce_links_input",
    "extract_citation_keys",
    "grounds_from_openai_citations",
    "grounds_from_tool_call_refs",
    "link_set_from_openai_citations",
    "parse_grounds",
    "parse_openai_citations",
]
