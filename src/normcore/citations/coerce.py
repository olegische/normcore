"""Normalization helpers for citation/link inputs."""

from __future__ import annotations

from typing import Iterable

from loguru import logger
from pydantic import ValidationError

from ..models.links import LinkSet
from .openai_adapter import (
    OpenAICitation,
    link_set_from_openai_citations,
    parse_openai_citations,
)

def coerce_links_input(
    *,
    links: LinkSet | dict | list | None,
    openai_citations: Iterable[OpenAICitation] | None,
) -> LinkSet | None:
    """Normalize caller citation inputs into a ``LinkSet``.

    Priority:
    1. Explicit ``links`` payload.
    2. OpenAI citations payload.
    """
    if links is not None:
        if isinstance(links, LinkSet):
            return links
        if isinstance(links, dict):
            try:
                return LinkSet.model_validate(links)
            except ValidationError as exc:
                logger.warning(f"Invalid links dict ignored: {exc}")
                return None
        if isinstance(links, list):
            if not links:
                logger.warning("Unsupported links list payload ignored")
                return None
            try:
                typed = parse_openai_citations(links)
            except ValidationError as exc:
                logger.warning(f"Invalid links list citations ignored: {exc}")
                return None
            return link_set_from_openai_citations(typed)
        logger.warning("Unsupported links payload type ignored")
        return None

    if not openai_citations:
        return None

    try:
        typed = parse_openai_citations(openai_citations)
    except ValidationError as exc:
        logger.warning(f"Invalid openai_citations ignored: {exc}")
        return None
    return link_set_from_openai_citations(typed)
