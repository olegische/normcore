"""
Link candidate matching from run artifacts.

Structural/heuristic approach to suggest StatementGroundLinks.

CRITICAL DESIGN PRINCIPLE:
--------------------------
LinkMatcher suggests CANDIDATE links, not VALID links.

Suggestion ≠ Validation:
- Suggestion: "This ground MIGHT support this statement" (heuristic)
- Validation: "This link is AUTHORIZED and CORRECT" (epistemic firewall)

Validation is decided ONLY in LinksBuilder (L1-L5).
If you enforce authority here → you duplicate firewall logic → system breaks.

WARNING: This is where semantic laundering can leak in.
         DO NOT add:
         - LLM-based similarity
         - Semantic embeddings
         - Content interpretation
         - "Smart" inference
         
         ONLY:
         - Structural patterns (entity mention)
         - Formal indicators (explicit references)
         - Deterministic heuristics

CONSERVATIVE ASSUMPTION v0.3.0:
-------------------------------
Structural matching (entity mention) is CONSERVATIVE approximation of usage.

Cost: May create false positive links (entity mentioned but not used).
Benefit: Prevents missing critical grounds (entity used → definitely mentioned).

LinksBuilder MUST validate and reject false positives via L1-L5.

This separation preserves:
- LinkMatcher: High recall (suggest all plausible)
- LinksBuilder: High precision (accept only valid)

KNOWN LIMITATIONS v0.3.0:
-------------------------
These are ACKNOWLEDGED limitations, not bugs.
They explain current A5 violations in runs.

1. **ID MISMATCH (БЛОКЕР интеграции):**
   
   Ground IDs не совпадают с KnowledgeStateBuilder node IDs.
   
   Problem:
   - KnowledgeStateBuilder: id = f"tool_{tool_name}_{hash(str(tool_result))}"
   - LinkMatcher: ground_id = f"tool_get_issue_{hash(content_str)}"
   - Different hash inputs → different IDs
   
   Result:
   - Links unusable by evaluator (ground_id not found in GroundSet)
   - Evaluator sees incomplete grounding → blocks ASSERTIVE → A5 violation
   
   Fix (v0.3.1):
   - Option A: Add semantic_id field to KnowledgeNode
   - Option B: Sync hash algorithm via shared utility
   
   This is the PRIMARY reason links don't work yet.

2. **Entity mention ≠ usage (false positives):**
   
   Example:
   Statement: "Jump in on AGENT-8. Why: AGENT-7 is blocked by AGENT-2."
   
   Matcher creates:
   - AGENT-8 → SUPPORTS ✓ (correct, decision about AGENT-8)
   - AGENT-7 → SUPPORTS ✗ (false positive, mentioned but not used for grounding)
   - AGENT-2 → SUPPORTS ✗ (false positive, tangential context)
   
   Cost: Noise in SUPPORTS set, may inflate required scopes.
   Acceptable: High-recall structural heuristic, validated by LinksBuilder.

3. **No DISAMBIGUATES detection:**
   
   Example:
   "AGENT-8 (State Management)" → matcher treats as SUPPORTS
   
   Should be:
   - AGENT-8 data → SUPPORTS
   - "(State Management)" → DISAMBIGUATES (parenthetical clarification)
   
   Impact:
   - DISAMBIGUATES incorrectly counted as SUPPORTS
   - May inflate required scopes (violates L5)
   - Harder to grant ASSERTIVE
   
   Fix (v0.3.1): H2 heuristic for parenthetical patterns.

4. **No dependency chains:**
   
   Statement may use:
   - "AGENT-8 blocks AGENT-4" (dependency relationship)
   - "AGENT-7 blocked by AGENT-2" (negative argument)
   - Epic context, business impact (indirect grounding)
   
   Matcher extracts only: Direct entity mentions.
   
   Missing: Structural relationships, comparative arguments, context propagation.
   
   Fix (v0.4): Graph-based structural analysis (still NOT semantic).

5. **No CONTEXTUALIZES detection:**
   
   Example:
   "AGENT-8 aligns with your goal" → matcher treats as SUPPORTS
   
   Should be:
   - AGENT-8 data → SUPPORTS
   - "your goal" reference → CONTEXTUALIZES
   
   Impact: Personalization incorrectly treated as grounding.
   
   Fix (v0.3.1): H3 heuristic for personalization patterns.

EXPECTED BEHAVIOR v0.3.0:
-------------------------
Given these limitations, current runs show A5 violations.

This is NOT evaluator error.
This is matcher providing incomplete link set.

Evaluator correctly sees:
- Incomplete SUPPORTS (due to ID mismatch)
- False positive SUPPORTS (due to entity mention)
- Missing DISAMBIGUATES/CONTEXTUALIZES (due to no detection)
→ Insufficient grounding for ASSERTIVE
→ A5 violation (correct enforcement)

v0.3.1 will fix ID mismatch + basic role detection.
v0.4 will add dependency chains + structural analysis.

v0.4 TODO: More sophisticated structural analysis (dependency graphs, coreference).
           NOT semantic interpretation.
"""

import json
import re
from typing import List, Dict, Any, Set, Tuple, Optional
from loguru import logger

from .models import StatementGroundLink, LinkRole, CreatorType, EvidenceType, Provenance

# NEW v0.3.2: Use same statement extraction as validator (avoid duplicate logic)
from src.evaluator.normative.statement_extractor import StatementExtractor


class LinkMatcher:
    """
    Suggest candidate StatementGroundLinks from run artifacts.
    
    Uses structural/heuristic analysis to identify potential links.
    
    Per FORMAL_SPEC_v0.3.md §3.5 Link Validation Pipeline:
    - Step 1: Link Creation Request (this component)
    - Step 2-4: LinksBuilder validates (separate component)
    - Step 5: Evaluator uses validated links
    
    CRITICAL: Matcher suggests CANDIDATES, not validated links.
    
    Heuristics (v0.3.0 - conservative):
    - H1: Entity Mention (if issue_key in statement → candidate SUPPORTS link)
    - H2: Disambiguation Detection (parenthetical clarifications → DISAMBIGUATES)
    - H3: Personalization Detection ("for you", "your goal" → CONTEXTUALIZES)
    
    All suggestions marked with creator=UPSTREAM_PIPELINE, evidence=STRUCTURAL.
    LinksBuilder decides if creator is authorized.
    
    NEW v0.3.2: Uses StatementExtractor (same as validator) to avoid logic duplication.
    """
    
    def __init__(self):
        """Initialize with StatementExtractor (shared with validator)."""
        self.extractor = StatementExtractor()
    
    def suggest_links(self, run_data: Dict[str, Any]) -> List[StatementGroundLink]:
        """
        Suggest candidate links from run artifacts.
        
        IMPORTANT: Returns CANDIDATE links, not VALIDATED links.
        
        This method performs structural heuristics only.
        It does NOT:
        - Validate authority (LinksBuilder does this via L1-L3)
        - Enforce role semantics (LinksBuilder does this via L4-L5)
        - Check provenance integrity (LinksBuilder does this)
        
        Args:
            run_data: Run JSON with messages, tool results, etc.
        
        Returns:
            List of candidate StatementGroundLinks (unvalidated)
        """
        messages = run_data.get("messages", [])
        if not messages:
            logger.warning("LinkMatcher: No messages in run_data")
            return []
        
        # 1. Extract statement using StatementExtractor (same logic as validator)
        final_message = self._get_final_agent_message(messages)
        if not final_message:
            logger.warning("LinkMatcher: No final agent message found")
            return []
        
        agent_output = final_message.get("content", "")
        statements = self.extractor.extract(agent_output)
        
        if not statements:
            logger.info("LinkMatcher: No normative content (protocol-only output)")
            return []
        
        # v0.1 single-statement model
        statement = statements[0]
        statement_text = statement.raw_text
        statement_id = statement.id
        
        # 2. Extract tool results (potential grounds)
        tool_results = self._extract_tool_results(messages, before_message=final_message)
        
        # 3. Apply heuristics to suggest links
        candidate_links = []
        
        # H1: Entity mention heuristic
        candidate_links.extend(self._apply_entity_mention_heuristic(
            statement_id, statement_text, tool_results
        ))
        
        # H2: Disambiguation detection (future)
        # H3: Personalization detection (future)
        
        # 4. Deduplicate (same statement_id + ground_id + role)
        unique_links = self._deduplicate_links(candidate_links)
        
        logger.info(
            f"LinkMatcher: Suggested {len(unique_links)} unique links "
            f"({len(candidate_links) - len(unique_links)} duplicates removed)"
        )
        
        return unique_links
    
    def _get_final_agent_message(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Get final agent/assistant message.
        
        Args:
            messages: List of message dicts
        
        Returns:
            Final agent message dict or empty dict
        """
        for msg in reversed(messages):
            if msg.get("role") in ("assistant", "agent") and msg.get("content"):
                return msg
        return {}
    
    def _extract_tool_results(
        self, 
        messages: List[Dict],
        before_message: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract tool call results from messages (before final statement).
        
        CRITICAL: Only include tool results BEFORE final statement.
        Tool results AFTER statement cannot ground it (temporal ordering).
        
        Args:
            messages: All messages
            before_message: Final statement message (temporal boundary)
        
        Returns:
            List of tool result dicts
        """
        tool_results = []
        
        for msg in messages:
            # Stop at final statement (don't include future tool calls)
            if msg == before_message:
                break
            
            # Extract tool results from role='tool' messages
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                tool_results.append({
                    "content": content,
                    "message": msg,
                })
        
        logger.debug(f"LinkMatcher: Extracted {len(tool_results)} tool results")
        return tool_results
    
    def _apply_entity_mention_heuristic(
        self,
        statement_id: str,
        statement_text: str,
        tool_results: List[Dict[str, Any]]
    ) -> List[StatementGroundLink]:
        """
        H1: Entity Mention Heuristic.
        
        If tool output contains entity_key AND statement mentions it
        → suggest SUPPORTS link (conservative).
        
        CONSERVATIVE ASSUMPTION:
        Entity mention ≈ entity usage for grounding.
        
        False positives possible:
        - "AGENT-7 is blocked by AGENT-2" mentions AGENT-7, but decision is about AGENT-8
        - Statement references entity tangentially, not for core grounding
        
        LinksBuilder MUST validate via L1-L5.
        Evaluator will use ONLY SUPPORTS links → false positives may over-conserve licensing.
        
        This is ACCEPTABLE cost for determinism + high recall.
        
        Args:
            statement_id: Statement ID (from StatementExtractor)
            statement_text: Statement raw text
            tool_results: Tool outputs (potential grounds)
        
        Returns:
            List of candidate SUPPORTS links
        """
        links = []
        seen_entities = set()  # Track which entities already linked
        
        for tool_result in tool_results:
            content_str = tool_result.get("content", "")
            
            try:
                # Try to parse as JSON
                data = json.loads(content_str)
                
                # Handle arrays (search_issues, search_users, etc.)
                if isinstance(data, list):
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        
                        # Convention-based: extract {entity_type}_key or {entity_type}_id
                        entity_id = self._extract_entity_id(item)
                        if not entity_id:
                            continue
                        
                        # Check if entity mentioned in statement
                        entity_value = entity_id.split('_', 1)[1]  # "issue_AGENT-8" → "AGENT-8"
                        
                        if entity_value in statement_text:
                            # Avoid duplicate links for same entity
                            if entity_value in seen_entities:
                                continue
                            seen_entities.add(entity_value)
                            
                            # CRITICAL v0.3.1: Use semantic_id format
                            ground_id = entity_id  # Already in format: "{type}_{value}"
                            
                            # Create candidate link
                            link = StatementGroundLink(
                                statement_id=statement_id,
                                ground_id=ground_id,
                                role=LinkRole.SUPPORTS,
                                provenance=Provenance(
                                    creator=CreatorType.UPSTREAM_PIPELINE,
                                    evidence_type=EvidenceType.STRUCTURAL,
                                    evidence_content=f"Entity mention heuristic: {entity_value} found in tool output (array) and statement"
                                )
                            )
                            links.append(link)
                            
                            logger.debug(
                                f"LinkMatcher H1 (array): {statement_id} → {ground_id} (entity: {entity_value})"
                            )
                    
                    continue  # Done with this array result
                
                # Handle single dict (get_issue, get_epic, etc.)
                if not isinstance(data, dict):
                    continue
                
                # Convention-based: extract {entity_type}_key or {entity_type}_id
                entity_id = self._extract_entity_id(data)
                if not entity_id:
                    continue
                
                # Check if entity mentioned in statement
                entity_value = entity_id.split('_', 1)[1]  # "issue_AGENT-8" → "AGENT-8"
                
                if entity_value in statement_text:
                    # Avoid duplicate links for same entity
                    if entity_value in seen_entities:
                        continue
                    seen_entities.add(entity_value)
                    
                    # CRITICAL v0.3.1: Use semantic_id format
                    # KnowledgeStateBuilder extracts semantic_id from tool results
                    # GroundSet.resolve_ground() resolves via semantic_id
                    # 
                    # Semantic ID format: "{entity_type}_{entity_value}"
                    # This matches KnowledgeNode.semantic_id field
                    ground_id = entity_id
                    
                    # Create candidate link
                    link = StatementGroundLink(
                        statement_id=statement_id,
                        ground_id=ground_id,
                        role=LinkRole.SUPPORTS,  # Conservative: assume core grounding
                        provenance=Provenance(
                            creator=CreatorType.UPSTREAM_PIPELINE,
                            evidence_type=EvidenceType.STRUCTURAL,
                            evidence_content=f"Entity mention heuristic: {entity_value} found in tool output and statement"
                        )
                    )
                    links.append(link)
                    
                    logger.debug(
                        f"LinkMatcher H1: {statement_id} → {ground_id} (entity: {entity_value})"
                    )
            
            except json.JSONDecodeError:
                # Not JSON, skip
                continue
        
        return links
    
    def _deduplicate_links(
        self, 
        links: List[StatementGroundLink]
    ) -> List[StatementGroundLink]:
        """
        Remove duplicate links (same statement_id + ground_id + role).
        
        CRITICAL: Deduplication prevents duplicate entries in LinkSet.
        
        If same link suggested multiple times (e.g., entity mentioned in multiple tools)
        → keep first occurrence only.
        
        Args:
            links: Candidate links (may have duplicates)
        
        Returns:
            Unique links
        """
        seen = set()
        unique = []
        
        for link in links:
            key = (link.statement_id, link.ground_id, link.role)
            if key not in seen:
                seen.add(key)
                unique.append(link)
        
        return unique
    
    def _extract_entity_id(self, data: dict) -> Optional[str]:
        """
        Extract primary entity ID from dict via convention.
        
        Convention (from tools generation prompt):
        - All entities have {entity_type}_id or {entity_type}_key field
        - Semantic ID = "{entity_type}_{value}"
        
        Priority order (first match wins):
        1. *_key fields (Jira: issue_key, epic_key, project_key)
        2. *_id fields (Bank: transaction_id, client_id, reservation_id, train_id, etc.)
        
        Domain-agnostic: works for any domain following convention.
        
        Args:
            data: Entity dict
        
        Returns:
            Semantic ID in format "{entity_type}_{value}" or None
        """
        import re
        
        # Pattern: {entity_type}_key or {entity_type}_id
        key_pattern = re.compile(r'^(\w+)_key$')
        id_pattern = re.compile(r'^(\w+)_id$')
        
        # Priority 1: *_key fields (Jira convention)
        for field_name, value in data.items():
            match = key_pattern.match(field_name)
            if match and value:
                entity_type = match.group(1)
                return f"{entity_type}_{value}"
        
        # Priority 2: *_id fields (Bank/Restaurant/Railway convention)
        for field_name, value in data.items():
            match = id_pattern.match(field_name)
            if match and value:
                entity_type = match.group(1)
                return f"{entity_type}_{value}"
        
        return None

