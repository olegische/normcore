"""Ground and citation-key primitives for internal link construction."""

from __future__ import annotations

import re
from typing import Iterable, Any

from pydantic import ValidationError
from pydantic import BaseModel, TypeAdapter

from ..logging import logger
from ..models.links import (
    CreatorType,
    EvidenceType,
    LinkRole,
    LinkSet,
    Provenance,
    StatementGroundLink,
)

_CITATION_KEY_PATTERN = re.compile(r"\[@([A-Za-z][A-Za-z0-9_-]*)\]")


class Ground(BaseModel):
    """Public ground input with a citation key and resolved ground id."""

    citation_key: str
    ground_id: str
    role: LinkRole = LinkRole.SUPPORTS
    creator: CreatorType = CreatorType.UPSTREAM_PIPELINE
    evidence_type: EvidenceType = EvidenceType.OBSERVATION
    evidence_content: str | None = None
    signature: str | None = None


_grounds_adapter = TypeAdapter(list[Ground])


def parse_grounds(grounds: Iterable[object] | None) -> list[Ground]:
    """Validate caller-supplied grounds payload."""
    if not grounds:
        return []
    return _grounds_adapter.validate_python(list(grounds))


def extract_citation_keys(text: str) -> list[str]:
    """Extract citation keys in ``[@key]`` format preserving first-seen order."""
    if not text:
        return []

    keys: list[str] = []
    seen: set[str] = set()
    for match in _CITATION_KEY_PATTERN.finditer(text):
        key = match.group(1)
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def build_links_from_grounds(
    *,
    text: str,
    grounds: Iterable[Ground],
    statement_id: str,
) -> LinkSet:
    """Build StatementGroundLinks by resolving text citation keys against grounds."""
    by_key: dict[str, list[Ground]] = {}
    for ground in grounds:
        by_key.setdefault(ground.citation_key, []).append(ground)

    links: list[StatementGroundLink] = []
    for key in extract_citation_keys(text):
        for ground in by_key.get(key, []):
            links.append(
                StatementGroundLink(
                    statement_id=statement_id,
                    ground_id=ground.ground_id,
                    role=ground.role,
                    provenance=Provenance(
                        creator=ground.creator,
                        evidence_type=ground.evidence_type,
                        evidence_content=ground.evidence_content or f"citation_key={key}",
                        signature=ground.signature,
                    ),
                )
            )

    return LinkSet(links=links)


def grounds_from_tool_call_refs(tool_call_refs: dict[str, list[str]]) -> list[Ground]:
    """Convert internal tool_call_id->ground_id mapping into grounds with keys."""
    grounds: list[Ground] = []
    for citation_key, ground_ids in tool_call_refs.items():
        for ground_id in ground_ids:
            grounds.append(
                Ground(
                    citation_key=citation_key,
                    ground_id=ground_id,
                    role=LinkRole.SUPPORTS,
                    creator=CreatorType.TOOL_OBSERVER,
                    evidence_type=EvidenceType.OBSERVATION,
                    evidence_content=f"tool_call_id={citation_key}",
                )
            )
    return grounds


def coerce_grounds_input(
    *,
    grounds: Iterable[object] | None,
    legacy_openai_citations: Iterable[Any] | None = None,
    legacy_links: Any | None = None,
) -> list[Ground]:
    """Normalize public grounds payload with legacy compatibility."""
    normalized: list[Ground] = []
    payload = list(grounds) if grounds else []

    if payload:
        try:
            # Canonical internal shape: list[Ground].
            normalized.extend(parse_grounds(payload))
        except ValidationError:
            try:
                # Public API shape: OpenAI annotations.
                from .openai_adapter import parse_openai_citations, grounds_from_openai_citations

                typed_citations = parse_openai_citations(payload)
                normalized.extend(grounds_from_openai_citations(typed_citations))
            except ValidationError as exc:
                logger.warning(f"Invalid grounds ignored: {exc}")

    if legacy_openai_citations:
        try:
            # Local import avoids import cycle (openai_adapter imports Ground from this module).
            from .openai_adapter import parse_openai_citations, grounds_from_openai_citations

            typed_citations = parse_openai_citations(legacy_openai_citations)
            normalized.extend(grounds_from_openai_citations(typed_citations))
        except ValidationError as exc:
            logger.warning(f"Invalid openai_citations ignored: {exc}")

    if legacy_links is not None:
        logger.warning("`links` input is deprecated and ignored; use `grounds`")

    return normalized
