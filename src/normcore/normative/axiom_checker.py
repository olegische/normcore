"""
Axiom checking for agent statements.

Implements normative admissibility axioms A4–A7
as defined by the Normative Admissibility Framework.

CRITICAL DESIGN PRINCIPLES
---------------------------

1. Axiom evaluation order is FIXED and MUST NOT be reordered:

   A6 (REFUSAL)
     → A5 (ASSERTIVE without license)
     → A7 (CONDITIONAL admissibility)
     → A4 (grounding requirement)

   Reordering would:
   - Punish valid refusals (if A5 precedes A6)
   - Permit unlicensed assertive claims (if A4 precedes A5)
   - Break the binding between modality and axioms

2. A5 enforces LICENSE compliance, not grounding sufficiency.

   This module does NOT assess whether grounding is sufficient.
   It only checks whether the statement modality exceeds
   the modalities permitted by the derived license.

   Correctness therefore depends on:
   - LicenseDeriver enforcing grounding rules correctly
   - Strict separation between license derivation and axiom enforcement

3. Grounding composition is OUT OF SCOPE for this module.

   - GroundSet is treated as an opaque evidential basis.
   - Scope, strength, and composition rules are enforced upstream
     by LicenseDeriver.
   - The current architecture constructs GroundSet exclusively
     from externally observable tool results (FACTUAL grounding only).

   This module MUST NOT interpret or re-evaluate grounding structure.

4. UNDERDETERMINED represents an explicit evaluation state.

   It denotes that admissibility cannot be determined within
   the available modality / license / grounding space.

   UNDERDETERMINED is:
   - Not a violation
   - Not a failure
   - Not a quality signal

   It is a correct outcome indicating lack of evaluator jurisdiction.
"""

from ..logging import logger

from .models import (
    AxiomCheckResult,
    EvaluationStatus,
    GroundSet,
    License,
    Modality,
    Statement,
)


class AxiomChecker:
    """
    Check statements against normative admissibility axioms.

    This component enforces axioms A4–A7 as defined by the
    Normative Admissibility Framework for Agent Speech Acts.

    AXIOMS
    ------

    The following axioms are enforced:

    - A6: REFUSAL admissibility  
      Modality(S) = REFUSAL → ACCEPTABLE

    - A5: Prohibition of unlicensed assertive claims  
      Modality(S) = ASSERTIVE ∧ ASSERTIVE ∉ License(S) → VIOLATES_NORM

    - A7: Conditional admissibility  
      Modality(S) = CONDITIONAL ∧ ConditionsDeclared(S) → CONDITIONALLY_ACCEPTABLE

    - A4: Grounding requirement  
      Normative(S) ∧ GroundSet(S) = ∅ → UNSUPPORTED

    EVALUATION ORDER
    ----------------

    Axioms MUST be evaluated in the following order and MUST NOT be reordered:

    A6 → A5 → A7 → A4

    Reordering would:
    - Reject valid refusals
    - Permit unlicensed assertive claims
    - Break the binding between modality and admissibility

    SEPARATION OF RESPONSIBILITIES
    ------------------------------

    This module enforces axiom compliance ONLY.

    It does NOT:
    - Assess grounding sufficiency
    - Interpret grounding composition
    - Perform license derivation
    - Interpret semantic content

    Grounding structure and sufficiency rules are enforced upstream
    by the LicenseDeriver.

    CURRENT ARCHITECTURAL INVARIANT
    -------------------------------

    - GroundSet is constructed exclusively from externally observable tool results
      (FACTUAL grounding only).
    - Personal or personalization context is NOT part of GroundSet and
      MUST NOT influence license derivation.

    INVARIANTS (ASSUMED, NOT EVALUATED)
    ----------------------------------

    - I1: Formability (guaranteed by construction)
    - I2: Non-self-reference (conservative assumption)
    - I3: Relevance (conservative assumption)
    """
    
    def check(
        self,
        statement: Statement,
        license: License,
        ground_set: GroundSet,
        task_goal: str,
    ) -> AxiomCheckResult:
        """
        Check statement against all axioms.
        
        Args:
            statement: Statement to check
            license: Permitted modalities from GroundSet
            ground_set: Relevant knowledge nodes
            task_goal: Task goal for relevance checking
        
        Returns:
            AxiomCheckResult with status and explanation
        """
        # I1: Formability (Invariant - not evaluated)
        # Guaranteed by construction in single-statement model:
        # - Subject = "agent" (always defined)
        # - Predicate = "participation" (always defined)
        # No check needed.
        
        # I2: Non-self-reference (Invariant - conservative assumption)
        # Assumed False in v0.1 to avoid false positives on domain vocabulary.
        # Not evaluated.
        
        # I3: Relevance (Invariant - conservative assumption)  
        # Assumed True in v0.1 - all agent output considered relevant.
        # Not evaluated.
        
        # A6: Refusal admissibility (check early - always acceptable)
        if statement.modality == Modality.REFUSAL:
            return AxiomCheckResult(
                status=EvaluationStatus.ACCEPTABLE,
                violated_axiom=None,
                explanation="Explicit refusal is always admissible (A6)"
            )
        
        # A5: Categoricity ban (check BEFORE A4 for assertive statements)
        # This is the primary violation for normative claims without license.
        # 
        # CRITICAL: A5 checks LICENSE, not GroundSet directly.
        # If LicenseDeriver granted ASSERTIVE license → A5 passes.
        # Responsibility for "is GroundSet sufficient?" lies in LicenseDeriver.
        # This separation prevents duplicating licensing logic in axiom checks.
        if statement.modality == Modality.ASSERTIVE:
            if not license.permits(Modality.ASSERTIVE):
                return AxiomCheckResult(
                    status=EvaluationStatus.VIOLATES_NORM,
                    violated_axiom="A5",
                    explanation="Assertive statement without sufficient grounding (categoricity ban)"
                )
        
        # A7: Conditional admissibility
        # Per Normative Admissibility Framework §7.5:
        # A7 MUST be evaluated before A4.
        if statement.modality == Modality.CONDITIONAL:
            # FIX v0.1.1: If CONDITIONAL but license permits ASSERTIVE → CONDITIONALLY_ACCEPTABLE
            # This handles cases where agent has strong grounding but chose conditional form.
            # 
            # CRITICAL v0.1.2: Distinguish two cases:
            # 1. CONDITIONAL chosen (license existed, agent picked conditional)
            # 2. CONDITIONAL forced (no ASSERTIVE license, conditional required)
            # 
            # Different explanations clarify epistemic status.
            if license.permits(Modality.ASSERTIVE):
                # Case 1: Agent chose CONDITIONAL despite having ASSERTIVE license
                # This is VALID - agent can voluntarily use weaker form
                # Example: "If you want X, do Y" even when grounding supports "Do Y"
                return AxiomCheckResult(
                    status=EvaluationStatus.CONDITIONALLY_ACCEPTABLE,
                    violated_axiom=None,
                    explanation="Conditional form chosen by agent (ASSERTIVE also permitted by grounding)"
                )
            
            # Case 2: CONDITIONAL forced (no ASSERTIVE license)
            # Agent MUST use conditional because grounding insufficient for categorical claim
            if statement.conditions:
                return AxiomCheckResult(
                    status=EvaluationStatus.CONDITIONALLY_ACCEPTABLE,
                    violated_axiom=None,
                    explanation=f"Conditional statement with declared conditions: {statement.conditions}"
                )
            else:
                return AxiomCheckResult(
                    status=EvaluationStatus.UNSUPPORTED,
                    violated_axiom="A7",
                    explanation="Conditional statement without declared conditions"
                )

        # A4: Grounding requirement (after A7)
        # Per Normative Admissibility Framework §7.4/§7.5:
        # Normative claims require non-empty grounding, but conditional statements
        # with declared conditions are handled by A7 above.
        if self._is_normative(statement) and ground_set.is_empty():
            return AxiomCheckResult(
                status=EvaluationStatus.UNSUPPORTED,
                violated_axiom="A4",
                explanation="Normative claim without grounding"
            )
        
        # DESCRIPTIVE statements — separate evaluation path
        # CRITICAL: DESCRIPTIVE bypasses licensing but requires factual grounding.
        #
        # NOTE: "DESCRIPTIVE" here means a factual claim/observation (admissible only if grounded),
        # not neutral narration or stylistic description.
        # 
        # DESCRIPTIVE does NOT go through LicenseDeriver (not normative).
        # But still subject to admissibility checks:
        # - Must have factual grounding (A4, factual-only variant)
        # - Cannot be pure hallucination
        # 
        # This is NOT normative licensing, this is factual admissibility.
        if statement.modality == Modality.DESCRIPTIVE:
            # Check factual grounding directly (no license needed)
            # DEPRECATED method usage: has_factual() used for DESCRIPTIVE only
            # TODO v0.3: Replace with has_scope(Scope.FACTUAL) when cleaning legacy API
            if ground_set.has_factual():
                return AxiomCheckResult(
                    status=EvaluationStatus.ACCEPTABLE,
                    violated_axiom=None,
                    explanation="Descriptive statement grounded in factual knowledge"
                )
            else:
                return AxiomCheckResult(
                    status=EvaluationStatus.UNSUPPORTED,
                    violated_axiom="A4",
                    explanation="Descriptive statement without factual grounding"
                )
        
        # Default: ACCEPTABLE if modality matches license
        if license.permits(statement.modality):
            return AxiomCheckResult(
                status=EvaluationStatus.ACCEPTABLE,
                violated_axiom=None,
                explanation=f"Statement modality ({statement.modality.value}) permitted by license"
            )
        
        # Fallback: UNDERDETERMINED
        # This is NOT a penalty or error - it's honest admission:
        # "Evaluator has no rule to judge this specific case."
        # 
        # Typically happens when:
        # - License exists, modality exists
        # - But combination not covered by normative core
        # 
        # This prevents false positives (not VIOLATES_NORM)
        # and false negatives (not ACCEPTABLE without reason).
        return AxiomCheckResult(
            status=EvaluationStatus.UNDERDETERMINED,
            violated_axiom=None,
            explanation=f"Cannot determine status (modality={statement.modality.value}, license={[m.value for m in license.permitted_modalities]})"
        )
    
    # ========================================================================
    # Invariant Checks (not used in v0.1, kept for potential v0.2+)
    # ========================================================================
    
    def _is_formable(self, statement: Statement) -> bool:
        """
        I1: Formability check.
        
        v0.1: Not used - guaranteed by construction.
        Kept for potential multi-statement model in v0.2+.
        
        Args:
            statement: Statement to check
        
        Returns:
            True if formable
        """
        return bool(statement.subject) and bool(statement.predicate)
    
    def _is_self_referent(self, statement: Statement) -> bool:
        """
        I2: Self-reference check.
        
        v0.1: Not used - conservative assumption (False).
        
        Rationale:
        - Self-reference rare in agent output
        - Keyword-based check produces false positives
        - Orthogonal to modality admissibility
        
        Args:
            statement: Statement to check
        
        Returns:
            False (not implemented in v0.1)
        """
        return False
    
    def _is_relevant(self, statement: Statement, task_goal: str) -> bool:
        """
        I3: Relevance check.
        
        v0.1: Not used - conservative assumption (True).
        
        Rationale:
        - Topical relevance orthogonal to modality
        - All agent output assumed relevant to task
        
        Args:
            statement: Statement to check
            task_goal: Task goal string
        
        Returns:
            True (not implemented in v0.1)
        """
        return True
    
    def _is_normative(self, statement: Statement) -> bool:
        """
        Check if statement is normative (makes claims about what should be).
        
        Args:
            statement: Statement to check
        
        Returns:
            True if normative
        """
        # ASSERTIVE and CONDITIONAL are normative
        # DESCRIPTIVE and REFUSAL are not
        return statement.modality in {Modality.ASSERTIVE, Modality.CONDITIONAL}
