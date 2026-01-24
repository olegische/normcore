"""
LinkBuilder service - validates and creates StatementGroundLinks.

Per FORMAL_SPEC_v0.3.md §3 Epistemic Firewall.

CRITICAL DESIGN PRINCIPLES:
---------------------------
1. LinksBuilder is GATEKEEPER, not inference engine.
   
   Decides WHICH links can be created (authority validation).
   Does NOT infer "statement uses this ground" (semantic interpretation).
   
   Links come from:
   - LinkMatcher (structural heuristics) → validated here
   - Agent declarations (future) → validated here
   - Human annotations (future) → accepted directly

2. Epistemic Firewall = separation between link creation and evaluation.
   
   LinksBuilder enforces L1-L5 axioms (WHO can create links).
   Evaluator trusts links (assumes LinksBuilder enforced rules).
   
   This prevents:
   - Agent self-licensing (L1)
   - LLM tool semantic laundering (L2)
   - Circular reasoning (L3)

3. v0.3.0 LIMITATIONS (acknowledged):
   
   a) Link axioms L1-L5 NOT fully enforced yet:
      
      Currently implemented:
      - L4 partial: All links created with role-aware semantics
      - Basic deduplication
      - Provenance tracking
      
      NOT implemented (v0.3.1 TODO):
      - L1: No self-licensing check (requires agent declaration detection)
      - L2: LLM tool guard (requires epistemic_class metadata)
      - L3: Authority validation (requires creator certification)
      - L5: DISAMBIGUATES scope neutrality (requires scope inference)
      
      CONSERVATIVE POLICY v0.3.0:
      All candidate links accepted (high recall, low precision).
      This may create false positive links → over-conservative licensing.
      
      This is ACCEPTABLE for v0.3.0 because:
      - False positives → over-block ASSERTIVE → safe (not dangerous)
      - False negatives → miss critical grounds → dangerous (not acceptable)
   
   b) ID mismatch with evaluator (BLOCKS integration):
      
      Links use ground_id that doesn't match KnowledgeNode.id from evaluator.
      
      Cause:
      - LinkMatcher: hash(content_str)
      - KnowledgeStateBuilder: hash(str(tool_result))
      - Different inputs → different hashes
      
      Result:
      - Evaluator cannot find grounds referenced by links
      - Links ignored, licensing falls back to v0.2 conservative mode
      - Expected A5 violations (incomplete grounding)
      
      Fix (v0.3.1):
      - Sync hash algorithm OR add semantic_id to KnowledgeNode
   
   c) Matcher limitations (see link_matcher.py for full list):
      
      - Entity mention ≠ usage (false positive SUPPORTS)
      - No DISAMBIGUATES detection (parenthetical patterns)
      - No CONTEXTUALIZES detection (personalization markers)
      - No dependency chain extraction
      
      These are structural heuristic limits, not bugs.
   
   v0.3.1 will fix (a) L1-L5 validation + (b) ID sync + basic role detection.
   v0.4 will address (c) advanced structural analysis.

4. Separation from Evaluator:
   
   LinksBuilder runs BEFORE evaluation (offline or pipeline step).
   Evaluator consumes LinkSet as input (does not create links).
   
   This enables:
   - Deterministic evaluation (same links → same license)
   - Auditable link provenance (WHO created, WHY)
   - No circular reasoning (evaluator doesn't grant own licenses)

WARNING: Any attempt to make this "smarter" via LLM inference
         destroys epistemic firewall and enables semantic laundering.
"""

import json
import os
from typing import Dict, Any
from loguru import logger

from .models import LinkSet, StatementGroundLink, LinkRole, CreatorType
from .link_matcher import LinkMatcher


class LinkBuilderService:
    """
    Validate and create StatementGroundLinks for normative evaluation.
    
    Implements epistemic firewall per FORMAL_SPEC_v0.3.md §3.
    
    Flow:
    1. Load run artifacts (messages, tool results)
    2. LinkMatcher suggests candidate links (structural heuristics)
    3. Validate candidates (L1-L5 axioms) [v0.3.1 TODO]
    4. Create LinkSet with provenance
    5. Save to .links.json (consumed by evaluator)
    
    CRITICAL v0.3.0 LIMITATION:
    L1-L5 validation NOT fully implemented yet.
    All candidate links accepted (conservative: high recall).
    
    This is safe because false positives → over-conservative licensing.
    v0.3.1 will add proper epistemic firewall validation.
    """
    
    def __init__(self):
        """Initialize LinkBuilder components."""
        self.matcher = LinkMatcher()
    
    def load_run(self, file_path: str) -> Dict[str, Any]:
        """
        Load run JSON from file.
        
        Args:
            file_path: Path to run JSON file
        
        Returns:
            Run data dict
        
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Run file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def build_links(self, run_data: Dict[str, Any]) -> LinkSet:
        """
        Build validated LinkSet from run artifacts.
        
        CRITICAL v0.3.0: Currently accepts all candidate links (no L1-L5 validation).
        
        This is CONSERVATIVE policy:
        - High recall (don't miss critical grounds)
        - Low precision (may include false positives)
        - Safe (false positives → over-conservative licensing, not dangerous)
        
        v0.3.1 will add proper validation.
        
        Args:
            run_data: Run JSON with messages, tool results, etc.
        
        Returns:
            LinkSet with validated links
        """
        # 1. Get candidate links from matcher (structural heuristics)
        candidate_links = self.matcher.suggest_links(run_data)
        
        logger.info(
            f"LinkBuilderService: LinkMatcher suggested {len(candidate_links)} candidate links"
        )
        
        # 2. Validate candidates (L1-L5)
        # v0.3.0: Accept all candidates (no validation yet)
        # v0.3.1 TODO: Implement _validate_link(link) → LinkValidation
        validated_links = candidate_links  # Temporary: no filtering
        
        # 3. Create LinkSet
        link_set = LinkSet(links=validated_links)
        
        logger.info(
            f"LinkBuilderService: Created LinkSet with {len(validated_links)} validated links"
        )
        
        # 4. Log summary
        role_counts = {}
        for link in validated_links:
            role_counts[link.role] = role_counts.get(link.role, 0) + 1
        
        logger.info(
            f"LinkBuilderService: Role distribution: {dict(role_counts)}"
        )
        
        return link_set
    
    # ========================================================================
    # Link Validation (v0.3.1 TODO - epistemic firewall)
    # ========================================================================
    
    def _validate_link(self, link: StatementGroundLink) -> bool:
        """
        Validate link against L1-L5 axioms.
        
        v0.3.1 TODO: Implement epistemic firewall validation.
        
        L1 — No Self-Licensing:
            Agent CANNOT create SUPPORTS links without validation.
            if link.provenance.creator == AGENT_DECLARATION:
                if link.role == SUPPORTS and not validated:
                    REJECT
        
        L2 — LLM Tool Guard:
            LLM tools CANNOT create SUPPORTS links.
            if link.provenance.creator == TOOL_OBSERVER:
                if tool.epistemic_class == "llm_proxy":
                    REJECT
        
        L3 — SUPPORTS Authority:
            SUPPORTS require: human OR non-LLM tool OR certified pipeline.
            if link.role == SUPPORTS:
                if creator not in {HUMAN, TOOL_OBSERVER, UPSTREAM_PIPELINE}:
                    REJECT
        
        L4 — CONTEXTUALIZES Exclusion:
            CONTEXTUALIZES links NEVER participate in sufficiency checks.
            (Enforced in evaluator, not here)
        
        L5 — DISAMBIGUATES Scope Neutrality:
            DISAMBIGUATES do NOT add scopes.
            (Enforced in evaluator, not here)
        
        Args:
            link: Candidate link
        
        Returns:
            True if link is valid, False otherwise
        """
        # v0.3.0: Accept all (no validation)
        # v0.3.1: Implement L1-L3 checks
        return True
    
    # ========================================================================
    # Utility methods
    # ========================================================================
    
    def save_links(self, link_set: LinkSet, output_path: str) -> None:
        """
        Save LinkSet to JSON file.
        
        Convention: file.json → file.links.json
        
        Args:
            link_set: LinkSet to save
            output_path: Output file path (e.g., "run_trial0.links.json")
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(link_set.dict(), f, indent=2, default=str)
        
        logger.info(f"LinkBuilderService: Saved {len(link_set.links)} links to {output_path}")
    
    def generate_links(self, run_data: Dict[str, Any]) -> LinkSet:
        """
        Legacy method name for backward compatibility.
        
        DEPRECATED: Use build_links() instead.
        """
        logger.warning("LinkBuilderService.generate_links() is deprecated, use build_links()")
        return self.build_links(run_data)

