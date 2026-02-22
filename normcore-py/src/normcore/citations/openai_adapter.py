"""OpenAI citation adapters for NormCore citation subsystem."""

from __future__ import annotations

import json
from collections.abc import Iterable

from openai.types.responses.response_output_text import Annotation
from pydantic import TypeAdapter

from ..models.links import (
    CreatorType,
    EvidenceType,
    LinkRole,
    LinkSet,
    Provenance,
    StatementGroundLink,
)
from .grounds import Ground

OpenAICitation = Annotation
_openai_citations_adapter = TypeAdapter(list[OpenAICitation])


def parse_openai_citations(citations: Iterable[object]) -> list[OpenAICitation]:
    """Validate citation payload against OpenAI SDK schema."""
    return _openai_citations_adapter.validate_python(list(citations))


def link_set_from_openai_citations(
    citations: Iterable[OpenAICitation],
    *,
    statement_id: str = "s1",
    role: LinkRole = LinkRole.SUPPORTS,
    creator: CreatorType = CreatorType.UPSTREAM_PIPELINE,
    evidence_type: EvidenceType = EvidenceType.OBSERVATION,
    signature: str | None = None,
) -> LinkSet:
    """Convert typed OpenAI citations into internal ``LinkSet``."""
    links: list[StatementGroundLink] = []

    for idx, citation in enumerate(citations):
        ground_id = _extract_ground_id(citation)
        if not ground_id:
            continue

        links.append(
            StatementGroundLink(
                statement_id=statement_id,
                ground_id=ground_id,
                role=role,
                provenance=Provenance(
                    creator=creator,
                    evidence_type=evidence_type,
                    evidence_content=_build_evidence_content(citation, idx),
                    signature=signature,
                ),
            )
        )

    return LinkSet(links=links)


def grounds_from_openai_citations(citations: Iterable[OpenAICitation]) -> list[Ground]:
    """Convert typed OpenAI citations into grounds keyed by their canonical id."""
    grounds: list[Ground] = []
    for citation in citations:
        ground_id = _extract_ground_id(citation)
        if not ground_id:
            continue
        grounds.append(
            Ground(
                citation_key=ground_id,
                ground_id=ground_id,
                creator=CreatorType.UPSTREAM_PIPELINE,
                evidence_type=EvidenceType.OBSERVATION,
                evidence_content="openai_citation",
            )
        )
    return grounds


def _extract_ground_id(citation: OpenAICitation) -> str | None:
    annotation_type = getattr(citation, "type", None)
    if annotation_type in {"file_citation", "container_file_citation", "file_path"}:
        file_id = getattr(citation, "file_id", None)
        return file_id.strip() if isinstance(file_id, str) and file_id.strip() else None
    if annotation_type == "url_citation":
        url = getattr(citation, "url", None)
        return url.strip() if isinstance(url, str) and url.strip() else None
    return None


def _build_evidence_content(citation: OpenAICitation, index: int) -> str:
    payload = citation.model_dump(mode="json")
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(rendered) > 1000:
        rendered = f"{rendered[:997]}..."
    return f"openai_citation[{index}]={rendered}"
