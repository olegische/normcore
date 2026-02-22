"""Backward-compatible re-exports for citation adapters.

New code should import from ``normcore.citations``.
"""

from ..citations.openai_adapter import (
    OpenAICitation,
    link_set_from_openai_citations,
    parse_openai_citations,
)

__all__ = [
    "OpenAICitation",
    "link_set_from_openai_citations",
    "parse_openai_citations",
]
