"""
Data models for StatementGroundLinks.

Per FORMAL_SPEC_v0.3.md §2 StatementGroundLinks and §3 Epistemic Firewall.

CRITICAL INVARIANTS:
--------------------
1. Links are DECLARATIONS, not INFERENCES.
   Link = "Statement S uses Ground G for Role R" (explicit claim)
   NOT = "Evaluator infers S might use G" (semantic interpretation)

2. Links created OUTSIDE evaluator.
   LinksBuilder validates and creates links BEFORE evaluation.
   Evaluator TRUSTS links (assumes LinksBuilder enforced L1-L5).

3. Provenance is MANDATORY.
   Every link: WHO created, WHEN created, HOW justified.
   Untraceable links → rejected.

4. Role semantics determine licensing impact:
   - SUPPORTS: Core grounding (required for license, checked for sufficiency)
   - DISAMBIGUATES: Clarification (optional, does NOT add scopes)
   - CONTEXTUALIZES: Personalization (NEVER affects licensing)

5. Creator authority hierarchy (per L1-L3):
   - HUMAN: Always trusted
   - TOOL_OBSERVER: Trusted if epistemic_class=OBSERVER (not LLM)
   - UPSTREAM_PIPELINE: Trusted if certified
   - AGENT_DECLARATION: NOT trusted without VALIDATION

SEPARATION OF CONCERNS:
-----------------------
- StatementExtractor: Extracts statements from agent output
- LinkMatcher: Suggests candidate links (heuristic/structural)
- LinksBuilder: Validates links (enforces L1-L5, creates provenance)
- Evaluator: Consumes links (derives license from SUPPORTS links only)

NO RESPONSIBILITY LEAKAGE between components.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LinkRole(str, Enum):
    """
    Role of ground in relation to statement.

    Per FORMAL_SPEC_v0.3.md §2.3 LinkRole (Usage Semantics).

    CRITICAL DISTINCTION:
    - SUPPORTS: Determines required scopes (licensing impact)
    - DISAMBIGUATES: Clarifies existing grounds (no new scopes)
    - CONTEXTUALIZES: Personalization only (never affects licensing)

    Examples:
    - "Jump in on AGENT-8" ← AGENT-8 blocking data (SUPPORTS)
    - "AGENT-8 (State Management)" ← taxonomy clarification (DISAMBIGUATES)
    - "AGENT-8 aligns with your goal" ← user preference (CONTEXTUALIZES)
    """

    SUPPORTS = "supports"  # Core grounding (required for license)
    DISAMBIGUATES = "disambiguates"  # Clarification (optional, no license impact)
    CONTEXTUALIZES = "contextualizes"  # Personalization (never affects license)


class CreatorType(str, Enum):
    """
    Who created the link.

    Per FORMAL_SPEC_v0.3.md §2.4 Provenance (Mandatory Tracking).

    Authority hierarchy (L1-L3):
    - HUMAN: Always authorized
    - TOOL_OBSERVER: Authorized if epistemic_class=OBSERVER (not LLM)
    - UPSTREAM_PIPELINE: Authorized if certified
    - AGENT_DECLARATION: NOT authorized without VALIDATION
    """

    HUMAN = "human"
    TOOL_OBSERVER = "tool_observer"
    AGENT_DECLARATION = "agent_declaration"
    UPSTREAM_PIPELINE = "upstream_pipeline"


class EvidenceType(str, Enum):
    """
    Type of evidence supporting link creation.

    Per FORMAL_SPEC_v0.3.md §2.4 Evidence types.

    - OBSERVATION: Direct observation (tool result content)
    - EXPLICIT: User/expert stated
    - STRUCTURAL: Syntactic/formal (e.g., entity mention heuristic)
    - VALIDATION: Human reviewer approved agent declaration
    """

    OBSERVATION = "observation"
    EXPLICIT = "explicit"
    STRUCTURAL = "structural"
    VALIDATION = "validation"


class Provenance(BaseModel):
    """
    Metadata about link origin.

    Per FORMAL_SPEC_v0.3.md §2.4 Provenance.

    MANDATORY for all links.
    Enables audit trail: WHO created, WHEN, WHY (evidence).
    """

    creator: CreatorType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    evidence_type: EvidenceType
    evidence_content: str | None = None  # Description of heuristic/reasoning
    signature: str | None = None  # Cryptographic proof (optional but recommended)


class StatementGroundLink(BaseModel):
    """
    Explicit connection between Statement and Knowledge Node.

    Per FORMAL_SPEC_v0.3.md §2.2 StatementGroundLink Definition.

    CRITICAL: Link is a DECLARATION, not inference.
    - "Statement S uses Ground G for Role R"
    - Created by LinksBuilder (validated via L1-L5)
    - Consumed by Evaluator (trusted)

    Fields:
    - statement_id: Which statement uses this ground (from StatementExtractor)
    - ground_id: Which Knowledge Node is used (from KnowledgeStateBuilder)
    - role: HOW ground is used (SUPPORTS/DISAMBIGUATES/CONTEXTUALIZES)
    - provenance: WHO/WHEN/HOW link created (mandatory)
    """

    statement_id: str
    ground_id: str
    role: LinkRole
    provenance: Provenance


class LinkSet(BaseModel):
    """
    Collection of validated links for a session/run.

    Created by LinksBuilder after validation.
    Consumed by Evaluator for license derivation.
    """

    links: list[StatementGroundLink] = Field(default_factory=list)
