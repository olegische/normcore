"""
Data models for normative evaluator.

Per FORMAL_SPEC_v0.2.md and LOGICAL_DAG_SPEC_v0.1.md.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Modality(Enum):
    """
    Statement modality per Formal Spec v0.1.
    
    Determines permitted usage in activity context.
    """
    ASSERTIVE = "assertive"      # "X should Y" without condition
    CONDITIONAL = "conditional"  # "If A, then X should Y"
    REFUSAL = "refusal"          # "Cannot determine X"
    DESCRIPTIVE = "descriptive"  # "X blocks Y" (factual)


class Source(Enum):
    """
    Source of Knowledge Node.
    
    Maps from Mind DAG evidence_basis.type.
    """
    OBSERVED = "observed"      # Tool call result, direct observation
    EXPLICIT = "explicit"      # User stated directly
    INFERRED = "inferred"      # Inferred from behavior
    REPEATED = "repeated"      # Pattern observed multiple times


class Status(Enum):
    """
    Epistemic status of Knowledge Node.
    
    Inherited from Mind DAG node.status.
    """
    HYPOTHESIS = "hypothesis"  # Inferred, not confirmed
    CANDIDATE = "candidate"    # Plausible, awaiting confirmation
    CONFIRMED = "confirmed"    # Validated through repetition/explicit evidence


class Scope(Enum):
    """
    Scope of Knowledge Node for relevance matching.
    
    Determines which statements a K can ground.
    
    CRITICAL v0.2: Only FACTUAL and CONTEXTUAL scopes exist.
    NORMATIVE removed - normative claims are meta-level, not grounding scope.
    """
    FACTUAL = "factual"        # Observable facts (from tools, operations)
    CONTEXTUAL = "contextual"  # User context (conditions, constraints, motives)


class EvaluationStatus(Enum):
    """
    Final evaluation status per axiom checking.
    
    Maps to reward scores.
    
    NEW v0.2.1 (per FORMAL_SPEC_v0.2.1 §0.4.5):
    NO_NORMATIVE_CONTENT is a pre-evaluation filter result, NOT an evaluation status.
    It indicates Speech Act Segmentation Layer produced zero normative utterances.
    
    Distinction:
    - UNDERDETERMINED: Evaluator CANNOT judge (ambiguous/incomplete)
    - NO_NORMATIVE_CONTENT: Evaluator HAS NO JURISDICTION (protocol-only output)
    """
    WELL_FORMED = "well_formed"
    ILL_FORMED = "ill_formed"
    UNSUPPORTED = "unsupported"
    UNDERDETERMINED = "underdetermined"
    CONDITIONALLY_ACCEPTABLE = "conditionally_acceptable"
    VIOLATES_NORM = "violates_norm"
    ACCEPTABLE = "acceptable"
    NO_NORMATIVE_CONTENT = "no_normative_content"  # NEW v0.2.1: Pre-evaluation filter result


@dataclass
class Statement:
    """
    Elementary statement extracted from agent output.
    
    Subject-predicate structure with modality.
    """
    id: str
    subject: str                    # e.g., "AGENT-1", "priority"
    predicate: str                  # e.g., "should_be_prioritized", "is_blocked"
    raw_text: str                   # Original text span
    modality: Optional[Modality] = None
    conditions: list[str] = field(default_factory=list)  # If CONDITIONAL


@dataclass
class KnowledgeNode:
    """
    Knowledge atom admitted for use in grounding.
    
    Projected from Mind DAG or observed facts.
    
    CRITICAL v0.1.2:
    strength distinguishes tool-derived (earned) vs memory-derived (borrowed) licenses:
    - strong: observed/tool-derived → grants ASSERTIVE
    - weak: memory-injected → only CONDITIONAL (disambiguation only)
    
    CRITICAL v0.3.1:
    semantic_id enables LinkSet integration (StatementGroundLinks use semantic IDs).
    
    ID scheme:
    - id: Canonical ID (e.g., "tool_get_issue_1234") - internal use
    - semantic_id: Domain-meaningful ID (e.g., "issue_AGENT-8") - for linking
    
    LinkMatcher uses semantic_id format (deterministic from domain entities).
    GroundSet.resolve() tries both id and semantic_id.
    """
    id: str
    source: Source
    status: Status
    confidence: float
    scope: Scope
    strength: str = "strong"  # "strong" | "weak"
    semantic_id: Optional[str] = None  # NEW v0.3.1: For LinkSet integration
    
    def __post_init__(self):
        """Validate confidence range and strength."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")
        if self.strength not in {"strong", "weak"}:
            raise ValueError(f"Strength must be 'strong' or 'weak', got {self.strength}")


@dataclass
class GroundSet:
    """
    Set of Knowledge Nodes relevant to a Statement.
    
    Used for license derivation.
    
    CRITICAL v0.2 INVARIANT:
    GroundSet MUST be queried via scope-aware methods ONLY.
    Global epistemic checks removed to prevent global weakest-link poisoning.
    
    CRITICAL ASSUMPTION v0.2:
    Presence of grounding in a scope is treated as USAGE by statement.
    We lack fine-grained statement→ground dependency tracking.
    
    Conservative policy:
    - If contextual nodes present → assume statement MAY use them
    - Therefore apply scoped weakest-link to contextual strength
    
    This prevents false ASSERTIVE licenses for contextual claims.
    Cost: May over-conservatively block some factual claims when cognitive byproduct present.
    
    v0.3 TODO: Replace with explicit StatementGroundLinks tracking actual usage.
    
    Rationale per FORMAL_SPEC_v0.2.md §6:
    - Weakest link applies WITHIN scopes, not globally
    - Cognitive weakness does NOT block factual ASSERTIVE (when only factual used)
    - Preserve determinism and Option 2 (grounding-based licensing)
    """
    nodes: list[KnowledgeNode] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        """Check if GroundSet is empty."""
        return len(self.nodes) == 0
    
    def has_factual(self) -> bool:
        """
        Check if GroundSet contains factual knowledge.
        
        DEPRECATED v0.2: Use has_scope(Scope.FACTUAL) instead.
        Kept ONLY for backward compatibility with evaluator reports.
        DO NOT use for licensing logic.
        """
        return any(k.scope == Scope.FACTUAL for k in self.nodes)
    
    def has_observed(self) -> bool:
        """
        Check if GroundSet contains observed knowledge.
        
        DEPRECATED v0.2: Reporting only, DO NOT use for licensing.
        
        CRITICAL: Source-based checks are NOT scoped and can reintroduce
        channel-based warrant (semantic laundering). Use scope-aware methods only.
        """
        return any(k.source == Source.OBSERVED for k in self.nodes)
    
    # ========================================================================
    # Scope-aware methods (NEW in v0.2 - scoped weakest-link policy)
    # ========================================================================
    
    def has_scope(self, scope: Scope) -> bool:
        """
        Check if GroundSet contains any nodes with given scope.
        
        Args:
            scope: Scope to check for
        
        Returns:
            True if at least one node has this scope
        """
        return any(k.scope == scope for k in self.nodes)
    
    def get_scope_strength(self, scope: Scope) -> Optional[str]:
        """
        Get strength for nodes within given scope.
        
        CRITICAL v0.2: Intra-scope strongest-evidence aggregation.
        
        Returns STRONGEST available evidence within a scope:
        - If ANY strong node in scope → "strong"
        - If only weak nodes in scope → "weak"
        - If no nodes in scope → None
        
        This is NOT "weakest link" within scope.
        This is "strongest evidence wins" within scope.
        
        Weakest-link applies BETWEEN scopes (inter-scope):
        - If factual weak OR contextual weak → CONDITIONAL only
        
        Enables scope-specific licensing:
        - Factual-only claims → check factual scope strength only
        - Mixed claims → check both scopes, weakest between them wins
        
        NOTE: "strength" field is trusted as set by KnowledgeBuilder.
        External injection of strength values is prohibited by builder policy.
        v0.3 TODO: Make strength a computed property (derive from status+confidence).
        
        Args:
            scope: Scope to check
        
        Returns:
            "strong" | "weak" | None
        """
        scope_nodes = [k for k in self.nodes if k.scope == scope]
        
        if not scope_nodes:
            return None
        
        # Intra-scope aggregation: strongest evidence wins
        # If ANY strong node in scope → scope strength is "strong"
        if any(k.strength == "strong" for k in scope_nodes):
            return "strong"
        
        # Only weak nodes in scope
        return "weak"
    
    def get_nodes_by_scope(self, scope: Scope) -> list[KnowledgeNode]:
        """
        Get all nodes with given scope.
        
        Args:
            scope: Scope to filter by
        
        Returns:
            List of nodes with this scope
        """
        return [k for k in self.nodes if k.scope == scope]
    
    def has_strong_in_scope(self, scope: Scope) -> bool:
        """
        Check if GroundSet has strong nodes in given scope.
        
        Args:
            scope: Scope to check
        
        Returns:
            True if at least one strong node in scope
        """
        return any(
            k.scope == scope and k.strength == "strong"
            for k in self.nodes
        )
    
    # ========================================================================
    # Link resolution methods (NEW v0.3.1 - StatementGroundLinks support)
    # ========================================================================
    
    def resolve_ground(self, ground_id: str) -> Optional[KnowledgeNode]:
        """
        Resolve ground by ID (canonical or semantic).
        
        NEW v0.3.1: Enables LinkSet integration.
        
        StatementGroundLinks use semantic_id (e.g., "issue_AGENT-8").
        KnowledgeNodes have both canonical id and semantic_id.
        
        Resolution strategy:
        1. Try canonical id first (exact match)
        2. Fallback to semantic_id (for LinkSet compatibility)
        
        Args:
            ground_id: Ground ID from link (canonical or semantic)
        
        Returns:
            KnowledgeNode if found, None otherwise
        """
        # Try canonical ID first
        for node in self.nodes:
            if node.id == ground_id:
                return node
        
        # Fallback: semantic_id (for LinkSet)
        for node in self.nodes:
            if node.semantic_id and node.semantic_id == ground_id:
                return node
        
        return None


@dataclass
class License:
    """
    Permitted statement modalities given GroundSet.
    
    Central bridge concept from Logical DAG.
    """
    permitted_modalities: set[Modality] = field(default_factory=set)
    
    def permits(self, modality: Modality) -> bool:
        """Check if modality is permitted."""
        return modality in self.permitted_modalities


@dataclass
class AxiomCheckResult:
    """
    Result of axiom checking for a statement.
    
    Maps to final reward via status.
    """
    status: EvaluationStatus
    violated_axiom: Optional[str] = None
    explanation: str = ""


@dataclass
class StatementValidationResult:
    """
    Validation result for a single statement.
    
    Used in runtime validation to provide detailed per-statement feedback.
    """
    statement: Statement
    status: EvaluationStatus
    license: License
    ground_set: "GroundSet"
    violated_axiom: Optional[str] = None
    explanation: str = ""


@dataclass
class ValidationResult:
    """
    Runtime validation result for agent message.
    
    CRITICAL: This is for runtime validation, NOT post-hoc evaluation.
    Used in orchestrator to validate public speech acts before accepting them.
    
    Difference from RewardInfo:
    - RewardInfo: post-hoc metrics (reward, reward_breakdown) for RL/benchmarking
    - ValidationResult: runtime check (status, feedback_hint) for agent loop
    
    Fields:
    - status: Aggregated normative status (lexicographic)
    - licensed: Whether evaluator has jurisdiction to judge
    - can_retry: Whether agent can retry with feedback
    - feedback_hint: Suggested action for agent if validation fails
    - violated_axioms: List of violated axiom names
    - statement_results: Detailed per-statement results
    - explanation: Human-readable explanation
    """
    # Aggregated status
    status: EvaluationStatus  # ACCEPTABLE/VIOLATES_NORM/UNSUPPORTED/...
    licensed: bool  # False if UNDERDETERMINED (no jurisdiction)
    
    # Runtime guidance
    can_retry: bool  # Can agent regenerate with feedback?
    feedback_hint: Optional[str] = None  # What to tell agent to fix
    
    # Details
    violated_axioms: list[str] = field(default_factory=list)
    statement_results: list[StatementValidationResult] = field(default_factory=list)
    explanation: str = ""
    
    # Metadata
    num_statements: int = 0
    num_acceptable: int = 0
    personal_context_source: str = "unknown"
    personal_context_scope: str = "unknown"
    personal_context_present: bool = False
    grounds_accepted: int = 0
    grounds_cited: int = 0
