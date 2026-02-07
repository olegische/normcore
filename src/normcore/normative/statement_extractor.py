"""
Statement extraction from agent output.

This component isolates NORMATIVE UTTERANCES from raw agent text
and produces a single domain-agnostic Statement for admissibility evaluation.

Per Normative Admissibility Framework:
the framework evaluates participation in activity, not semantic truth.

DESIGN PRINCIPLES
-----------------
1) Domain-agnostic, form-based extraction.

   The extractor does NOT:
   - Parse domain objects or entities
   - Reconstruct ontologies
   - Interpret semantic content
   - Judge correctness or truth

   It operates solely on the FORM of agent output.

2) Single-statement participation model.

   - The agent's final output is treated as one speech act.
   - A generic Statement is constructed with:
       subject   = "agent"
       predicate = "participation"
   - Modality is determined later by ModalityDetector.

   This guarantees structural invariants by construction and avoids
   semantic parsing or LLM-as-judge patterns.

3) Pre-normative protocol filtering.

   Raw agent output contains two distinct layers:
   - PROTOCOL speech: greetings, offers, channel management
   - NORMATIVE speech: assertions, recommendations, refusals

   Protocol speech is NOT subject to normative axioms (A4–A7)
   and MUST be removed before evaluation.

   This component performs boundary-based filtering to:
   - Strip protocol-only prefixes and suffixes
   - Preserve only normative participation

   If no normative content remains, extraction returns an empty list,
   indicating that the evaluator has no jurisdiction to judge.

4) Deterministic, non-semantic implementation.

   - Filtering is based on formal textual indicators only.
   - No embeddings, similarity, or semantic heuristics are used.
   - Behavior is fully deterministic and auditable.

5) Personalization-aware normative participation.

   Context-relative framing (e.g. "for you", "given your preferences")
   is treated as normative participation and must not be dropped
   during protocol filtering.

   Such statements are preserved so that ModalityDetector can classify
   them as CONDITIONAL, without granting epistemic grounding.

NON-GOALS
---------
- Multi-statement extraction
- Semantic interpretation
- Capability or tool-availability validation
- Truth assessment

These concerns are explicitly out of scope.
"""

import re
from loguru import logger

from .models import Statement


class StatementExtractor:
    """
    Extract normative participation from agent output.

    This component performs PRE-NORMATIVE speech act segmentation.
    It isolates NORMATIVE UTTERANCES from raw agent text and constructs
    a single domain-agnostic Statement for admissibility evaluation.

    Per draft-romanchuk-normative-admissibility-00:
    the framework evaluates admissibility of participation in activity,
    not semantic truth or domain correctness.

    RESPONSIBILITY
    --------------
    - Separate protocol-level speech from normative participation
    - Preserve normative utterances for subsequent modality analysis
    - Construct a generic, domain-agnostic Statement object

    NON-RESPONSIBILITY
    ------------------
    This component does NOT:
    - Parse domain entities or objects
    - Interpret semantic content
    - Judge correctness, truth, or usefulness
    - Perform grounding or licensing
    - Determine modality

    DESIGN CHOICES
    --------------
    1) Single-statement participation model.

       - The agent's final output is treated as one speech act.
       - A generic Statement is constructed with:
           subject   = "agent"
           predicate = "participation"
       - Modality is derived later by ModalityDetector.

       This avoids semantic parsing and guarantees structural invariants
       by construction.

    2) Protocol vs normative separation.

       Raw agent output may contain:
       - PROTOCOL speech (greetings, offers, channel management)
       - NORMATIVE speech (assertions, recommendations, refusals)

       Protocol speech is conversation management and is NOT subject
       to normative admissibility axioms (A4–A7).

       This component removes protocol-only prefixes and suffixes
       before normative evaluation.

    3) Boundary-based, deterministic implementation.

       - Uses formal textual indicators only
       - No embeddings, similarity, or semantic heuristics
       - Fully deterministic and auditable

    4) Personalization-aware filtering.

       Context-relative framing (e.g. "for you", "given your preferences")
       is treated as normative participation and MUST NOT be dropped
       during protocol filtering.

       Such utterances are preserved so that ModalityDetector can classify
       them as CONDITIONAL without granting epistemic grounding.

    OUTPUT CONTRACT
    ---------------
    - Returns a list with a single Statement if normative participation exists
    - Returns an empty list if the output contains only protocol speech

    An empty result signals that the evaluator has no jurisdiction
    to judge the agent output.
    """
    
    # ========================================================================
    # Protocol Speech Detection Patterns (Formal Indicators)
    # ========================================================================
    #
    # ARCHITECTURAL PRINCIPLE:
    # Protocol detection = BOUNDARY detection, not content classification.
    #
    # Protocol speech has 3 structural properties (position, self-reference, open-ended):
    # - Position-bounded (prefix or suffix, rarely middle)
    # - Self-referential ("I can...", "How can I help...")
    # - Open-ended (question, offer, capability enumeration)
    #
    # Normative claims are opposite: closed, declarative, not inviting continuation.
    #
    # STRATEGY: Two-pass boundary cutting (suffix → prefix), not iterative strip.
    
    # NORMATIVE INDICATORS (check FIRST - early exit if absent)
    # These patterns signal potential normative content
    # Conservative: only add patterns with LOW false positive risk
    #
    # IMPLEMENTATION INVARIANT (crucial):
    # If ModalityDetector uses a formal indicator to classify a statement as
    # normative participation (ASSERTIVE/CONDITIONAL/REFUSAL/DESCRIPTIVE),
    # StatementExtractor MUST treat that indicator as sufficient to keep the
    # utterance for evaluation. Otherwise the evaluator can silently drop
    # normative participation before modality detection runs.
    NORMATIVE_INDICATORS = [
        # Strong normative markers
        r'\b(?:should|must|recommend|prioritize)\b',
        r'\bblock(?:s|ed|ing)?\b',
        r'\bdepends\s+on\b',
        r'\bis\s+(?:blocked|required|dependent)\b',

        # Recommendation framing that may omit "should/must"
        r'\bis\s+better\b',
        r'\bbetter\s+for\s+you\b',
        r'\bbest\s+(?:choice|option)\b',
        r'\bprefer(?:s|red)?\b',
        
        # Conditional structures
        r'\bif\s+.+\s+then\b',
        
        # Refusal markers
        r'\b(?:cannot|can\'t|unable\s+to)\s+determine\b',
        r'\bnot\s+enough\s+(?:info|information|context)\b',
        r'\b(?:need|require)\s+(?:more|additional)\b',
    ]

    # Personalization framing (non-epistemic context markers).
    #
    # These MUST count as normative participation even without "should/must"
    # to avoid dropping personalization claims before ModalityDetector runs.
    PERSONALIZATION_NORMATIVE_INDICATORS = [
        r'\bfor\s+you\b',
        r'\bgiven\s+your\b',
        r'\bbased\s+on\s+your\b',
        r'\baccording\s+to\s+your\b',
        r'\bwith\s+your\s+(?:preferences|constraints)\b',
    ]
    
    # SUFFIX PATTERNS (work from END - protocol tail detection)
    # Protocol speech almost never ends with normative claims
    PROTOCOL_SUFFIX_PATTERNS = [
        # Parenthetical examples/capabilities - "(e.g., X, Y, Z)"
        # Matches: (e.g., find issue, check status, ...) or (finding..., checking...)
        r'\s*\([^)]*(e\.g\.|for example|such as|find|check|status|comment|assign|move|create|pull|help|assist|transition|workflow)[^)]*\)\s*$',
        
        # Capability offers at end - "I can help with...", "Let me know if..."
        r'\s*(?:i\s+can\s+(?:help|assist|pull|check|find)|let\s+me\s+know\s+if|feel\s+free\s+to\s+ask).*$',
        
        # Question tail (only if contains help/assist keywords)
        # Avoids stripping normative questions like "Should we prioritize X?"
        r'\s*[^.!?]*(?:help|assist|can\s+i|would\s+you\s+like)\s*[^.!?]*\?\s*$',
    ]
    
    # PREFIX PATTERNS (work from START - protocol header detection)
    # Single-pass fat regex (not iterative strip)
    PROTOCOL_PREFIX_PATTERN = r"^(?:hello|hi|hey|greetings|good\s+(?:morning|afternoon|evening)|thanks\s+for\s+asking|i'?m\s+doing\s+(?:well|fine|good|great|okay|ok)|i'?m\s+(?:here|ready|available)|hope\s+you'?re\s+doing\s+well)[!,.\s—-]*"
    
    def extract(self, text: str) -> list[Statement]:
        """
        Extract statement from agent output.
        
        v0.1 Design: Single-statement model.
        - Agent's final response = one speech act
        - One speech act = one Statement
        - Modality determined separately (ModalityDetector)
        
        v0.3.2: Strip greeting prefix before extraction.
        - Greetings are protocol-level speech, not normative claims
        - Including them forces misclassification (default → ASSERTIVE → A5 violation)
        - Clean separation: protocol layer vs normative evaluation layer
        
        Args:
            text: Agent output (typically final message content)
        
        Returns:
            List with single Statement (or empty if no normative content after greeting removal)
        """
        if not text or not text.strip():
            logger.warning("StatementExtractor: Empty text provided")
            return []
        
        # Strip greeting prefix (protocol-level meta-communication)
        cleaned_text = self._strip_greeting(text)
        
        # If nothing remains after stripping → no normative content
        # Return empty list → evaluator will report NO_NORMATIVE_CONTENT (no jurisdiction)
        if not cleaned_text.strip():
            logger.info(
                "StatementExtractor: Only greeting/protocol speech detected, "
                "no normative content to evaluate"
            )
            return []
        
        # Create single statement representing agent's normative participation
        statement = Statement(
            id="final_response",
            subject="agent",           # Generic: who participates
            predicate="participation", # Generic: speech act in activity
            raw_text=cleaned_text,     # Cleaned: protocol prefix removed
        )
        
        logger.debug(
            f"StatementExtractor: Extracted single statement "
            f"(length={len(cleaned_text)} chars, preview: {cleaned_text[:80]}...)"
        )
        
        return [statement]
    
    def _contains_normative_indicators(self, text: str) -> bool:
        """
        Check if text contains any normative indicators.
        
        EARLY EXIT optimization: If text has zero normative indicators,
        it's likely pure protocol speech → skip segmentation entirely.
        
        This is NOT semantic classification. These are FORMAL INDICATORS
        of potential normative content (should/must/blocks/depends).
        
        Args:
            text: Text to check
        
        Returns:
            True if text contains normative indicators
        """
        text_lower = text.lower()
        for pattern in self.NORMATIVE_INDICATORS:
            if re.search(pattern, text_lower):
                return True
        for pattern in self.PERSONALIZATION_NORMATIVE_INDICATORS:
            if re.search(pattern, text_lower):
                return True
        return False

    def _contains_strong_normative_indicators(self, text: str) -> bool:
        """
        Check for "strong" normative indicators excluding pure personalization framing.

        Used to prevent personalization phrasing from turning protocol offers into
        normative participation.
        """
        text_lower = text.lower()
        for pattern in self.NORMATIVE_INDICATORS:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _looks_like_protocol_sentence(self, sentence: str) -> bool:
        """
        Check if sentence looks like protocol speech (not normative).
        
        Protocol markers (self-referential, open-ended):
        - "I can...", "How can I help...", "Thanks for asking"
        - Questions without normative content
        
        This is CHEAP HEURISTIC, not semantic analysis.
        
        Args:
            sentence: Single sentence to check
        
        Returns:
            True if sentence looks like protocol speech
        """
        s_lower = sentence.lower().strip()
        
        # Protocol markers
        protocol_markers = [
            r'\bi\s+can\b',
            r'\bhow\s+can\s+i\b',
            r'\bwhat\s+can\s+i\b',
            r'\bthanks\s+for\b',
            r'\blet\s+me\s+know\b',
            r'\bfeel\s+free\b',
            r'\bhope\s+you\b',
        ]
        
        for pattern in protocol_markers:
            if re.search(pattern, s_lower):
                return True
        
        # Questions are often protocol (unless contain normative indicators)
        if s_lower.endswith('?') and not self._contains_normative_indicators(s_lower):
            return True
        
        return False
    
    def _strip_protocol_prefix_sentences(self, text: str) -> str:
        """
        Strip protocol sentences from prefix.
        
        ALGORITHM:
        1. Split into sentences
        2. Walk from start
        3. Discard sentences that:
           - Look like protocol (self-referential, questions)
           - AND don't contain normative indicators
        4. Keep first normative sentence and everything after
        
        This handles multi-sentence protocol prefixes:
        "Hello! I'm doing well. How can I help? Task X blocks Y."
        → Keeps only: "Task X blocks Y."
        
        Args:
            text: Text to process
        
        Returns:
            Text with protocol prefix sentences removed
        """
        # Split on sentence boundaries (. ! ?)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        kept = []
        found_normative = False
        
        for i, sentence in enumerate(sentences):
            # If we already found normative content, keep everything after
            if found_normative:
                kept.append(sentence)
                continue
            
            has_strong_normative = self._contains_strong_normative_indicators(sentence)
            has_any_normative = self._contains_normative_indicators(sentence)

            # If sentence looks protocol and has no strong normative content,
            # discard it even if it contains personalization framing.
            if self._looks_like_protocol_sentence(sentence) and not has_strong_normative:
                continue

            # First normative sentence → keep it and everything after
            if has_any_normative:
                kept.extend(sentences[i:])
                found_normative = True
                break
            
            # Sentence is neither clearly protocol nor clearly normative
            # Conservative: keep it (might be normative without indicators)
            kept.append(sentence)
        
        return ' '.join(kept).strip()
    
    def _strip_protocol_suffix(self, text: str) -> str:
        """
        Strip protocol speech from suffix (end of text).
        
        CRITICAL: Suffix patterns MUST be anchored to $ (end of text).
        Protocol tail detection — if pattern doesn't match end, don't cut.
        
        Iterative: Protocol tails are often cascaded:
        "...(e.g., X, Y) I can help with Z"

        NOTE: This is a conservative heuristic and may over-filter in rare cases,
        e.g. "X is better for you (e.g., because you prefer quiet cabins)."
        
        Args:
            text: Text to process
        
        Returns:
            Text with protocol suffix removed
        """
        prev = None
        current = text.strip()
        
        # Iterate until no more changes (cascaded suffixes)
        max_iterations = 5
        iteration = 0
        
        while prev != current and iteration < max_iterations:
            prev = current
            
            for pattern in self.PROTOCOL_SUFFIX_PATTERNS:
                # CRITICAL: All patterns MUST have $ anchor
                # If pattern doesn't end with $, add it
                anchored_pattern = pattern if pattern.endswith('$') else pattern + r'$'
                
                current = re.sub(
                    anchored_pattern,
                    '',
                    current,
                    flags=re.IGNORECASE | re.DOTALL
                ).strip()
            
            iteration += 1
        
        return current
    
    def _strip_greeting(self, text: str) -> str:
        """
        Remove protocol-level speech from agent output via boundary-based filtering.

        This method implements PRE-NORMATIVE boundary detection.
        It separates protocol speech (conversation management) from
        normative participation before admissibility evaluation.

        SCOPE
        -----
        Protocol speech includes:
        - Greetings and small talk
        - Offers to help or continue the conversation
        - Capability lists and examples
        - Open-ended questions without normative content

        Normative speech includes:
        - Assertions, recommendations, refusals
        - Context-relative claims ("for you", "given your preferences")
        - Any utterance subject to modality classification

        ALGORITHM
        ---------
        1) Early exit:
           If no normative indicators are present, the output is treated
           as protocol-only and removed entirely.

        2) Suffix stripping (from the end):
           Remove protocol tails such as:
           - Capability lists
           - Examples
           - Offers to continue or assist

        3) Prefix stripping (from the start):
           Remove greetings and protocol headers, including multi-sentence
           conversational preambles.

        4) Final guard:
           If the remaining text ends with a question mark and contains
           no normative indicators, it is treated as protocol-only.

        DESIGN INVARIANTS
        -----------------
        - This is boundary detection, not content classification.
        - No semantic interpretation is performed.
        - Deterministic, regex-based implementation only.
        - Personalization framing counts as normative participation
          and MUST NOT be stripped.

        CONTRACT
        --------
        Args:
            text: Raw agent output.
    
        Returns:
            Cleaned text containing only normative participation,
            or an empty string if no such content remains.

        An empty result indicates that the evaluator has no jurisdiction
        to assess the agent output.
        """

        cleaned = text.strip()
        original_length = len(cleaned)
        
        # STEP 0: Early exit if no normative indicators
        # If text contains no "should/must/blocks/depends" → likely pure protocol
        if not self._contains_normative_indicators(cleaned):
            logger.debug(
                "StatementExtractor: No normative indicators found "
                "(likely protocol-only output)"
            )
            return ""  # Protocol-only → NO_NORMATIVE_CONTENT
        
        # STEP 1: Strip SUFFIX (protocol tail - capability lists, examples)
        # Anchored, iterative (handles cascaded suffixes)
        cleaned = self._strip_protocol_suffix(cleaned)
        
        # STEP 2: Strip PREFIX sentences (protocol header - greetings, small talk)
        # Multi-sentence protocol prefix stripping
        cleaned = self._strip_protocol_prefix_sentences(cleaned)
        
        # STEP 3: Strip PREFIX tokens (single-pass fat regex for remaining greeting tokens)
        cleaned = re.sub(
            self.PROTOCOL_PREFIX_PATTERN,
            "",
            cleaned,
            flags=re.IGNORECASE
        ).strip()
        
        # STEP 4: Hard invariant - question tail rejection
        # Questions are generally protocol speech (continuation invites), not activity participation.
        #
        # HOWEVER: some agent outputs are interrogative while still containing formal normative
        # indicators (e.g., "Should we prioritize X?"). Stripping those would create a cheap
        # evasion channel ("add '?' to avoid evaluation").
        #
        # Policy: reject only if the remaining core ends with "?" AND contains no normative indicators.
        if cleaned.endswith('?') and not self._contains_normative_indicators(cleaned):
            logger.debug(
                "StatementExtractor: Normative core ends with '?' - likely protocol, rejecting"
            )
            return ""  # Protocol-only
        
        # Log if anything was stripped
        if len(cleaned) < original_length:
            logger.debug(
                f"StatementExtractor: Stripped protocol speech "
                f"(original: {original_length} chars, cleaned: {len(cleaned)} chars)"
            )
        
        return cleaned
