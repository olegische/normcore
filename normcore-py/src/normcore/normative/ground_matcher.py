"""
GroundSet matching for normative admissibility evaluation.

This component selects potentially relevant KnowledgeNodes
from the available GroundSet for a given Statement.

CURRENT ARCHITECTURE (v0.3+)
----------------------------

- GroundSet is constructed exclusively from externally observable
  tool results (FACTUAL grounding only).
- Personalization or personal context is NOT part of GroundSet
  and MUST NOT influence relevance or licensing.

As a result, relevance matching is intentionally minimal.

DESIGN PRINCIPLE
----------------

GroundSetMatcher performs CANDIDATE SELECTION ONLY.

It determines whether a KnowledgeNode could, in principle,
participate in grounding a statement of a given modality.

It does NOT:
- Decide grounding sufficiency
- Perform epistemic evaluation
- Interpret semantic content
- Enforce licensing rules

Relevance ≠ Sufficiency.

Sufficiency and admissibility are determined exclusively
by LicenseDeriver and AxiomChecker.

RELEVANCE RULES (CURRENT)
-------------------------

- DESCRIPTIVE statements:
  Only FACTUAL knowledge nodes are considered relevant.

- ASSERTIVE / CONDITIONAL statements:
  FACTUAL knowledge nodes are considered candidates.
  (No contextual grounding exists in this architecture.)

- REFUSAL statements:
  No grounding is required or selected.

These rules define POTENTIAL relevance only.
Whether the resulting GroundSet is sufficient or admissible
is decided downstream.

SECURITY NOTE
-------------

This module MUST remain non-semantic and non-interpretive.

Do NOT add:
- Semantic matching
- Similarity scoring
- Embeddings
- Domain heuristics
- Task-specific logic

Doing so would violate determinism and introduce
implicit self-licensing paths.
"""

from ..logging import logger
from .models import (
    GroundSet,
    KnowledgeNode,
    Modality,
    Scope,
    Statement,
)


class GroundSetMatcher:
    """
    Match Knowledge Nodes to Statements.

    Relevance rules (v0.1 - simple scope-based):
    - DESCRIPTIVE → K.scope=FACTUAL (observations only)
    - ASSERTIVE/CONDITIONAL → K.scope ∈ {FACTUAL, CONTEXTUAL} (any knowledge)
    - REFUSAL → no grounds needed (A6)

    CRITICAL: These rules define POTENTIAL relevance, not SUFFICIENCY.

    Whether ASSERTIVE requires BOTH factual AND contextual,
    or just ONE confirmed knowledge, etc. → decided in LicenseDeriver.

    This separation prevents licensing logic from leaking into matching.
    """

    def match(
        self,
        statement: Statement,
        knowledge_nodes: list[KnowledgeNode],
    ) -> GroundSet:
        """
        Find potentially relevant Knowledge Nodes for a statement.

        IMPORTANT: Returns CANDIDATE grounds, not SUFFICIENT grounds.

        This method performs scope-based filtering only.
        It does NOT check:
        - Whether grounds are sufficient (LicenseDeriver does this)
        - Whether grounds have right status (LicenseDeriver does this)
        - Whether grounds semantically match content (we never do this)

        Args:
            statement: Statement to ground
            knowledge_nodes: Available knowledge

        Returns:
            GroundSet with candidate nodes (potentially relevant)
        """
        relevant = []

        for k in knowledge_nodes:
            if self._is_relevant(statement, k):
                relevant.append(k)

        logger.debug(
            f"GroundSetMatcher: Found {len(relevant)}/{len(knowledge_nodes)} relevant nodes "
            f"for statement '{statement.subject} {statement.predicate}'"
        )

        return GroundSet(nodes=relevant)

    def _is_relevant(self, statement: Statement, k: KnowledgeNode) -> bool:
        """
        Check if Knowledge Node is POTENTIALLY RELEVANT to Statement.

        CRITICAL: This is a CANDIDATE SELECTION, not sufficiency check.

        We include nodes that COULD support the statement type.
        LicenseDeriver decides if the set is SUFFICIENT.

        Args:
            statement: Statement
            k: Knowledge Node

        Returns:
            True if node is a candidate ground (potentially relevant)
        """
        # DESCRIPTIVE: factual observations only
        # Examples: "AGENT-1 blocks AGENT-2", "status is Done"
        # Only factual K can ground observations.
        if statement.modality == Modality.DESCRIPTIVE:
            return k.scope == Scope.FACTUAL

        # ASSERTIVE/CONDITIONAL: normative claims
        # Accept both CONTEXTUAL and FACTUAL as candidates.
        # - CONTEXTUAL = constraints, preferences, domain rules
        # - FACTUAL = observed data that can inform decisions
        #
        # LicenseDeriver will check if combination is sufficient.
        # We do NOT enforce "must have both" here - that's licensing logic.
        if statement.modality in {Modality.ASSERTIVE, Modality.CONDITIONAL}:
            return k.scope in {Scope.CONTEXTUAL, Scope.FACTUAL}

        # REFUSAL: no grounding needed (A6)
        # Explicit refusal is always acceptable without grounds.
        if statement.modality == Modality.REFUSAL:
            return False

        # Default: not relevant
        return False
