"""
Modality determination for statements.

Per Normative Admissibility Framework:
Modality is the logical form of participation in activity.

THEORETICAL FOUNDATION
----------------------
Modality is NOT a component of Statement.
It is a DERIVED characteristic established by formal analysis.

Formally:
    Statement := ⟨Subject, Predicate⟩
    Modality : Statement → {ASSERTIVE, CONDITIONAL, REFUSAL, DESCRIPTIVE}

This module implements the Modality function via FORMAL INDICATORS.

FORMAL INDICATORS
-----------------
Formal indicators are textual signs sufficient for classification
of statement form.

Indicators operate at the level of FORM, not SEMANTICS:
- No semantic interpretation
- No pragmatic speech-act analysis
- No content understanding
- Deterministic textual structure only

DETERMINATION METHOD
--------------------
1. Head-driven detection:
   Modality is determined by the CORE assertion
   (first paragraph or first sentence) only.

2. Detection priority (fixed):
   REFUSAL
   > GOAL-CONDITIONAL
   > PERSONALIZATION-CONDITIONAL
   > ASSERTIVE (recommendation)
   > CONDITIONAL
   > DESCRIPTIVE
   > ASSERTIVE (default)

   GOAL-CONDITIONAL and PERSONALIZATION-CONDITIONAL are detection
   subclasses of CONDITIONAL and exist to override recommendation markers
   (e.g. "X is better for you").

3. Default = ASSERTIVE is a POLICY choice (anti-evasion),
   not a logical necessity.

SEPARATION OF CONCERNS
----------------------
- StatementExtractor: isolates normative utterances
- ModalityDetector: classifies form only
- Grounding and licensing are handled elsewhere

Condition extraction (for CONDITIONAL):
- Extracted from full text
- Treated as declarative flags, not logical premises

LIMITATIONS
-----------
- English-only
- Formal-indicator based
- No semantic inference by design
"""

import re

from ..logging import logger
from .models import Modality, Statement


class ModalityDetector:
    """
    Determine statement modality from formal indicators.

    Implements the Modality function as defined in
    draft-romanchuk-normative-admissibility-00.

        Modality : Statement → {ASSERTIVE, CONDITIONAL, REFUSAL, DESCRIPTIVE}

    Modality is a DERIVED property of a statement's FORM,
    not an intrinsic attribute of the Statement object itself.

    Determination order (CRITICAL — MUST NOT be reordered):
    1. REFUSAL
       Explicit admission of inability to determine.
       Always admissible (A6).

    2. GOAL-CONDITIONAL
       Goal-conditional framing (e.g. "If your goal is X…").
       Syntactic subclass of CONDITIONAL.

    3. PERSONALIZATION-CONDITIONAL
       Context-relative framing (e.g. "for you", "given your preferences").
       Also a syntactic subclass of CONDITIONAL.
       Must override recommendation markers to prevent categorical
       claims based on non-epistemic personal context.

    4. ASSERTIVE (recommendation)
       Categorical recommendation expressed in the core assertion.

    5. CONDITIONAL
       Explicit conditional structure in the core assertion
       (A7 applies if conditions are declared).

    6. DESCRIPTIVE
       Factual observation without normative force
       (not subject to A5 licensing).

    7. ASSERTIVE (default)
       Anti-evasion policy: if no explicit refusal or condition is present,
       the statement is treated as categorical.

    This ordering ensures:
    - Explicit refusals are honored
    - Conditional framing is not misclassified as assertive
    - Personalization does not silently grant assertive force
    - Normative evasion via vague language is prevented
    """

    # Formal indicators for REFUSAL modality
    # CRITICAL: These detect EXPLICIT admission of inability to determine.
    # NOT "polite uncertainty" (maybe, possibly, likely) - those default to ASSERTIVE.
    # Per A6 (§5.1): explicit refusal is always acceptable when context is missing.
    # DO NOT expand without strong justification - risk of false REFUSAL.
    REFUSAL_FORM_INDICATORS = [
        r"cannot\s+(?:determine|decide|choose)",
        r"(?:need|require)\s+(?:more|additional)",
        r"insufficient",
        r"please\s+(?:provide|clarify|check)",
        r"I\s+don'?t\s+(?:know|have)",
        r"hard\s+to\s+(?:say|determine)",
        r"^i\s+(?:would|will)\s+not\s+\w+",
        r"^i\s+(?:wouldn't|won't)\s+\w+",
    ]

    # Formal indicators for CONDITIONAL modality
    CONDITIONAL_FORM_INDICATORS = [
        r"\b(?:if|unless|assuming|given\s+that|provided)\s+",
        r"depends\s+on",
        r"(?:would|could|might)\s+\w+\s+(?:if|when|unless)",
    ]

    # Goal-conditional indicators (MUST override recommendation indicators)
    # These force CONDITIONAL even if recommendation indicators present
    # "If your goal is X, do Y" is CONDITIONAL, not ASSERTIVE
    GOAL_CONDITIONAL_FORM_INDICATORS = [
        r"^if\s+(?:your\s+)?goal\s+is",
        r"^if\s+you\s+(?:want|care|optimize|aim)",
        r"^assuming\s+you\s+(?:want|care|optimize|aim)",
        r"^if\s+you'?re\s+(?:optimizing|aiming|trying)",
    ]

    # Personalization framing indicators.
    #
    # These are NOT epistemic facts. They are context-relative claims of the form:
    # "X is better for you" / "Given your preferences, ..."
    #
    # We classify them as CONDITIONAL to prevent categorical ASSERTIVE claims
    # from being licensed by non-epistemic personal context.
    PERSONALIZATION_CONDITIONAL_FORM_INDICATORS = [
        r"\bfor\s+you\b",
        r"\bgiven\s+your\b",
        r"\bbased\s+on\s+your\b",
        r"\baccording\s+to\s+your\b",
        r"\bwith\s+your\s+(?:preferences|constraints)\b",
    ]

    # Formal indicators for DESCRIPTIVE modality (factual, not normative)
    DESCRIPTIVE_FORM_INDICATORS = [
        r"\bblocks?\b",
        r"\bis\s+blocked\s+by\b",
        r"\bdepends?\s+on\b",
        r"\bhas\s+status\b",
        r"\bis\s+(?:In\s+Progress|Blocked|Done|To\s+Do)",
        r"\bdue\s+date\s+is\b",
    ]

    # Normative indicators (should/must) - support ASSERTIVE classification
    NORMATIVE_FORM_INDICATORS = [
        r"\bshould\b",
        r"\bmust\b",
        r"\bneeds?\s+to\b",
        r"\brecommend",
        r"\bsuggest",
        r"\badvise",
    ]

    # Recommendation indicators (for ASSERTIVE override)
    # If these present in core assertion, statement is ASSERTIVE even if conditional indicators in tail
    RECOMMENDATION_FORM_INDICATORS = [
        r"\b(?:is|are)\s+(?:the\s+)?better\b",
        r"\bshould\s+(?:be\s+)?(?:prioritiz|focus|pick|choose)",
        r"\brecommend\s+\w+",
        r"\bsuggest\s+(?:you\s+)?(?:pick|choose|start)",
        r"\bbest\s+(?:place|choice|option)",
        r"\bprioritize\s+(?:the\s+)?\w+",  # "Prioritize X"
        r"\b(?:finish|complete)\s+\w+\s+first\b",  # "Finish X first"
    ]

    def __init__(self) -> None:
        """Initialize detector with compiled formal indicators."""
        self._refusal_re = [re.compile(ind, re.IGNORECASE) for ind in self.REFUSAL_FORM_INDICATORS]
        self._conditional_re = [
            re.compile(ind, re.IGNORECASE) for ind in self.CONDITIONAL_FORM_INDICATORS
        ]
        self._goal_conditional_re = [
            re.compile(ind, re.IGNORECASE) for ind in self.GOAL_CONDITIONAL_FORM_INDICATORS
        ]
        self._personalization_conditional_re = [
            re.compile(ind, re.IGNORECASE)
            for ind in self.PERSONALIZATION_CONDITIONAL_FORM_INDICATORS
        ]
        self._descriptive_re = [
            re.compile(ind, re.IGNORECASE) for ind in self.DESCRIPTIVE_FORM_INDICATORS
        ]
        self._normative_re = [
            re.compile(ind, re.IGNORECASE) for ind in self.NORMATIVE_FORM_INDICATORS
        ]
        self._recommendation_re = [
            re.compile(ind, re.IGNORECASE) for ind in self.RECOMMENDATION_FORM_INDICATORS
        ]

    def detect(self, text: str) -> Modality:
        """
        Detect modality from text using HEAD-DRIVEN detection.

        CRITICAL FIX v0.1.2:
        - Core assertion determined by FIRST paragraph/sentence only
        - Supplementary clauses in tail do not change modality
        - Goal-conditional OVERRIDES recommendation markers
        - This prevents "Do X. [justification]. If you tell me Y, I can help" → CONDITIONAL (wrong)
        - AND prevents "If your goal is X, Y is better" → ASSERTIVE (wrong)

        Changes:
        v0.1.1: ASSERTIVE overrides CONDITIONAL if recommendation markers present
        v0.1.2: HEAD-DRIVEN detection + GOAL-CONDITIONAL priority

        Detection priority (FIXED, do not reorder):
        REFUSAL > GOAL-CONDITIONAL > PERSONALIZATION-CONDITIONAL > ASSERTIVE (recommendation) > CONDITIONAL > DESCRIPTIVE > ASSERTIVE (default)

        Why this order:
        - REFUSAL: Always acceptable (A6)
        - GOAL-CONDITIONAL: Deontic advice, not epistemic assertion
        - ASSERTIVE (recommendation): Categorical recommendation with grounding
        - CONDITIONAL: General conditional structure
        - DESCRIPTIVE: Factual observation
        - ASSERTIVE (default): Anti-evasion fallback

        Args:
            text: Statement text (typically raw_text field)

        Returns:
            Modality enum
        """
        text_lower = text.lower()

        # HEAD-DRIVEN DETECTION v0.1.2:
        # Extract core assertion (first paragraph or first sentence)
        # This prevents supplementary "if" clauses in tail from overriding core modality
        #
        # Examples:
        # - "Prioritize X. [justification]. If you tell me Y..." → core = "Prioritize X"
        # - "X is better. If you want to maximize..." → core = "X is better"
        # - "If X, then do Y." → core = "If X, then do Y"
        #
        # Split priority:
        # 1. Double newline (paragraph break)
        # 2. Single newline + next line starts with dash/number (list)
        # 3. First sentence (period + space)
        core = self._extract_core_assertion(text_lower)

        # 1. Check REFUSAL (highest priority)
        if self._is_refusal(core):
            logger.debug(f"Modality: REFUSAL for: {text[:60]}...")
            return Modality.REFUSAL

        # 2. Check GOAL-CONDITIONAL (BEFORE recommendation override)
        # CRITICAL v0.1.2: Goal-conditional MUST override recommendation markers
        #
        # "If your goal is X, do Y" is CONDITIONAL, NOT ASSERTIVE
        # Even if "do Y" contains "is better" or "should prioritize"
        #
        # This distinguishes:
        # - ASSERTIVE: "X is better" (categorical claim about world)
        # - CONDITIONAL: "If you want X, then Y is better" (deontic advice)
        #
        # Goal-conditional = recommendation conditioned on user's objectives
        # This is NOT the same as "X is better. If you tell me..."
        if self._is_goal_conditional(core):
            logger.debug(f"Modality: CONDITIONAL (goal-conditional) for: {text[:60]}...")
            return Modality.CONDITIONAL

        # 2.5. Check PERSONALIZATION framing (BEFORE recommendation override)
        # "X is better for you" / "Given your preferences, X ..." must be CONDITIONAL.
        # Policy: personalization framing upgrades otherwise-descriptive utterances into
        # normative participation (CONDITIONAL), because the claim is context-relative.
        if self._is_personalization_conditional(core):
            logger.debug(f"Modality: CONDITIONAL (personalization framing) for: {text[:60]}...")
            return Modality.CONDITIONAL

        # 3. Check ASSERTIVE with recommendation (BEFORE general conditional)
        # If core contains recommendation markers → ASSERTIVE
        # Even if conditional markers also present in full text
        if self._has_recommendation(core):
            logger.debug(f"Modality: ASSERTIVE (recommendation in core) for: {text[:60]}...")
            return Modality.ASSERTIVE

        # 4. Check CONDITIONAL (only if CORE is conditional)
        # This is the key fix: conditional markers in tail don't count
        if self._is_conditional(core):
            logger.debug(f"Modality: CONDITIONAL for: {text[:60]}...")
            return Modality.CONDITIONAL

        # 5. Check DESCRIPTIVE (factual, no normative claim)
        if self._is_descriptive(core) and not self._is_normative(core):
            logger.debug(f"Modality: DESCRIPTIVE for: {text[:60]}...")
            return Modality.DESCRIPTIVE

        # 6. Default: ASSERTIVE (anti-evasion POLICY)
        # CRITICAL v0.2: This is POLICY choice, not logical necessity
        # See module docstring §3 for full explanation
        # v0.3 may make this configurable (ModalityPolicy parameter)
        logger.debug(f"Modality: ASSERTIVE (default policy) for: {text[:60]}...")
        return Modality.ASSERTIVE

    def detect_with_conditions(self, statement: Statement) -> Statement:
        """
        Detect modality and extract conditions if CONDITIONAL.

        CRITICAL SEPARATION OF CONCERNS:

        1. Modality detection (ASSERTIVE/CONDITIONAL/REFUSAL/DESCRIPTIVE)
           → determined by CORE assertion only (head-driven)

        2. Condition extraction (if CONDITIONAL)
           → extracts from FULL TEXT (core + tail)
           → only happens when modality == CONDITIONAL

        This means:
        - ASSERTIVE with supplementary "if" in tail → no conditions extracted
        - CONDITIONAL → conditions extracted from full text (may include tail)

        Mutates statement.modality and statement.conditions.

        Args:
            statement: Statement to analyze

        Returns:
            Updated statement
        """
        modality = self.detect(statement.raw_text)
        statement.modality = modality

        # If conditional, extract conditions
        # CRITICAL: Only called when modality == CONDITIONAL
        # If ASSERTIVE (even with "if" in tail) → this branch not taken
        if modality == Modality.CONDITIONAL:
            statement.conditions = self._extract_conditions(statement.raw_text)

        return statement

    def _is_refusal(self, text: str) -> bool:
        """Check if text contains refusal form indicators."""
        return any(indicator.search(text) for indicator in self._refusal_re)

    def _is_conditional(self, text: str) -> bool:
        """Check if text contains conditional form indicators."""
        return any(indicator.search(text) for indicator in self._conditional_re)

    def _is_goal_conditional(self, text: str) -> bool:
        """
        Check if text is goal-conditional.

        CRITICAL v0.1.2:
        Goal-conditional = recommendation conditioned on user's objectives/goals.

        Examples:
        - "If your goal is X, do Y" → CONDITIONAL
        - "If you want to optimize for X, pick Y" → CONDITIONAL
        - "Assuming you care about X, Y is better" → CONDITIONAL

        This is DIFFERENT from:
        - "Do Y. If you want more info..." → ASSERTIVE (supplementary offer)

        Goal-conditional MUST force CONDITIONAL even if recommendation indicators present.
        This prevents misclassifying deontic advice as epistemic assertion.

        Returns:
            True if goal-conditional structure detected
        """
        return any(indicator.search(text) for indicator in self._goal_conditional_re)

    def _is_personalization_conditional(self, text: str) -> bool:
        """
        Check if core assertion is framed as personalization ("for you", "given your ...").

        This is treated as CONDITIONAL to prevent non-epistemic personal context
        from producing categorical ASSERTIVE claims.
        """
        return any(indicator.search(text) for indicator in self._personalization_conditional_re)

    def _is_descriptive(self, text: str) -> bool:
        """Check if text contains descriptive form indicators."""
        return any(indicator.search(text) for indicator in self._descriptive_re)

    def _is_normative(self, text: str) -> bool:
        """Check if text contains normative form indicators."""
        return any(indicator.search(text) for indicator in self._normative_re)

    def _has_recommendation(self, text: str) -> bool:
        """
        Check if text contains recommendation form indicators.

        Used to detect ASSERTIVE modality even when conditional indicators present in tail.
        Example: "X is better. If Y, consider Z" → ASSERTIVE (not CONDITIONAL)

        Returns:
            True if recommendation indicators present
        """
        return any(indicator.search(text) for indicator in self._recommendation_re)

    def _extract_core_assertion(self, text: str) -> str:
        """
        Extract core assertion from text (head-driven detection).

        CRITICAL v0.1.2:
        Only the CORE assertion determines modality.
        Supplementary clauses in tail are ignored for classification.

        Extraction strategy:
        1. If double newline exists → take first paragraph
        2. Else if list structure (line starts with -, *, number) → take first item
        3. Else take first sentence (up to period + space/newline)
        4. Else take first 500 chars (fallback)

        Examples:
        - "Prioritize X.\\n\\nJustification..." → "prioritize x."
        - "Do Y. If later..." → "do y."
        - "X is better. Context. If you tell me..." → "x is better."

        Args:
            text: Full text (already lowercased)

        Returns:
            Core assertion text
        """
        # Strategy 1: Double newline (paragraph break)
        if "\n\n" in text:
            core = text.split("\n\n")[0].strip()
            logger.debug(f"Core (paragraph): {core[:80]}...")
            return core

        # Strategy 2: First sentence (period + space or newline)
        # Match: ". " or ".\n" (end of sentence)
        import re

        sentence_match = re.search(r"^(.+?\.)\s", text, re.DOTALL)
        if sentence_match:
            core = sentence_match.group(1).strip()
            logger.debug(f"Core (sentence): {core[:80]}...")
            return core

        # Strategy 3: First line (if multiline without period)
        if "\n" in text:
            core = text.split("\n")[0].strip()
            logger.debug(f"Core (first line): {core[:80]}...")
            return core

        # Strategy 4: Fallback - first 500 chars
        core = text[:500].strip()
        logger.debug(f"Core (fallback 500): {core[:80]}...")
        return core

    def _extract_conditions(self, text: str) -> list[str]:
        """
        Extract condition clauses from conditional statement.

        CRITICAL INVARIANTS:

        1. Conditions are extracted from FULL TEXT, not only core assertion.
           This may include supplementary or future-facing conditions.

           Example:
           "If X, do Y. Later: if Z, I can help more."
           → extracts both X and Z

        2. This is ACCEPTABLE because conditions are DECLARATIVE FLAGS, not logical premises.
           We mark "agent declared conditions exist", not "agent claim depends on exactly these".

        3. GroundSetMatcher / LicenseDeriver MUST NOT assume:
           - Extracted conditions are minimal
           - Extracted conditions are necessary for the claim
           - Extracted conditions are the only conditions

        4. This method ONLY serves A7 (ConditionsDeclared check):
           "Did agent explicitly declare conditions, or claim unconditionally?"

        4.1 Personalization framing ("for you", "given your ...") is treated as an explicit
            condition for A7 purposes. This is a POLICY CHOICE.

        5. Conditions are FLAGS, not LOGIC:
           - We do NOT evaluate truth
           - We do NOT evaluate satisfiability
           - We do NOT evaluate coherence
           - "unless X" → "NOT X" is textual marker, not logical negation

        Returns:
            List of condition strings. If modality is CONDITIONAL but no extractable clause
            is found, returns ["unspecified"] as a sentinel indicating declared conditionality.
        """
        conditions = []

        # Try to extract if-clause
        if_match = re.search(r"\bif\s+([^,]+)", text, re.IGNORECASE)
        if if_match:
            conditions.append(if_match.group(1).strip())

        # Try to extract unless-clause (mark as negation, but don't evaluate)
        unless_match = re.search(r"\bunless\s+([^,]+)", text, re.IGNORECASE)
        if unless_match:
            # "NOT" prefix is a textual marker, not logical evaluation
            conditions.append(f"NOT {unless_match.group(1).strip()}")

        # Try to extract assuming/given-clause
        assuming_match = re.search(r"\b(?:assuming|given\s+that)\s+([^,]+)", text, re.IGNORECASE)
        if assuming_match:
            conditions.append(assuming_match.group(1).strip())

        # Personalization clauses (context markers)
        given_your_match = re.search(r"\bgiven\s+your\s+([^,.;]+)", text, re.IGNORECASE)
        if given_your_match:
            conditions.append(f"given your {given_your_match.group(1).strip()}")

        based_on_your_match = re.search(r"\bbased\s+on\s+your\s+([^,.;]+)", text, re.IGNORECASE)
        if based_on_your_match:
            conditions.append(f"based on your {based_on_your_match.group(1).strip()}")

        if re.search(r"\bfor\s+you\b", text, re.IGNORECASE):
            conditions.append("for you")

        return conditions if conditions else ["unspecified"]
