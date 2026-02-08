"""
License derivation from GroundSet.

This component derives the set of permitted statement modalities from the
available evidential grounding.

Per Normative Admissibility Framework:
- Inputs are Statement (S), GroundSet (G), Context (C).
- License is derived from GroundSet (G) only. Context is out of scope here.

DESIGN PRINCIPLES
-----------------
1) License regulates NORMATIVE speech acts only.
   - ASSERTIVE and CONDITIONAL are subject to licensing.
   - DESCRIPTIVE statements do NOT require a license (factual observation).
   - REFUSAL is always permitted (A6) and does not require licensing.

   INVARIANT: The evaluator MUST NOT call LicenseDeriver for DESCRIPTIVE modality.

2) LicenseDeriver is the sole authority for grounding sufficiency and permission rules.
   AxiomChecker must only enforce license compliance, not re-derive sufficiency.

3) Current architecture: GroundSet contains FACTUAL grounding only.
   - GroundSet is constructed exclusively from externally observable tool results.
   - Personalization / personal context is NOT part of GroundSet.
   - CONTEXTUAL grounding is intentionally not represented.

   Therefore, licensing depends solely on factual grounding strength.

4) Strength-based licensing rule (current architecture):
   - If GroundSet is empty → {REFUSAL}
   - If at least one FACTUAL node is strong → {ASSERTIVE, CONDITIONAL, REFUSAL}
   - Otherwise (FACTUAL present but weak) → {CONDITIONAL, REFUSAL}

5) Status elevation is forbidden.
   LicenseDeriver reads strength, and MUST NOT upgrade or infer epistemic status.

OPTIONAL v0.3 MODE: USAGE-BASED LICENSING (StatementGroundLinks)
---------------------------------------------------------------
When StatementGroundLinks are provided:
- Only grounds linked with role=SUPPORTS are considered "used".
- Licensing is derived from used grounds only.

When links are absent:
- Conservative mode applies: all grounds are treated as potentially used.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ..logging import logger

from .models import GroundSet, License, Modality, Scope

if TYPE_CHECKING:
    from ..models import LinkSet


class LicenseDeriver:
    def derive(self, ground_set: GroundSet, links: Optional["LinkSet"] = None) -> License:
        if links is not None:
            return self._derive_with_links(ground_set, links)
        return self._derive_conservative(ground_set)

    def _derive_conservative(self, ground_set: GroundSet) -> License:
        if ground_set.is_empty():
            logger.debug("License (conservative): REFUSAL only (empty GroundSet)")
            return License(permitted_modalities={Modality.REFUSAL})

        factual_strength = ground_set.get_scope_strength(Scope.FACTUAL)
        if factual_strength is None:
            logger.debug("License (conservative): REFUSAL only (no factual grounding)")
            return License(permitted_modalities={Modality.REFUSAL})

        if factual_strength == "strong":
            logger.debug("License (conservative): ASSERTIVE, CONDITIONAL, REFUSAL (strong factual)")
            return License(
                permitted_modalities={Modality.ASSERTIVE, Modality.CONDITIONAL, Modality.REFUSAL}
            )

        logger.debug("License (conservative): CONDITIONAL, REFUSAL (weak factual)")
        return License(permitted_modalities={Modality.CONDITIONAL, Modality.REFUSAL})

    def _derive_with_links(self, ground_set: GroundSet, links: "LinkSet") -> License:
        from ..models import LinkRole

        support_links = [link for link in links.links if link.role == LinkRole.SUPPORTS]
        if not support_links:
            logger.debug("License (with links): REFUSAL only (no SUPPORTS links)")
            return License(permitted_modalities={Modality.REFUSAL})

        used_grounds = []
        unresolved = []
        for link in support_links:
            ground = ground_set.resolve_ground(link.ground_id)
            if ground is None:
                unresolved.append(link.ground_id)
            else:
                used_grounds.append(ground)

        if unresolved:
            logger.warning(
                f"License (with links): Could not resolve {len(unresolved)} grounds: {unresolved[:3]}..."
            )

        if not used_grounds:
            logger.warning(
                "License (with links): REFUSAL only (all SUPPORTS links unresolved - ID mismatch?)"
            )
            return License(permitted_modalities={Modality.REFUSAL})

        factual_grounds = [g for g in used_grounds if g.scope == Scope.FACTUAL]
        if not factual_grounds:
            logger.debug("License (with links): REFUSAL only (no factual SUPPORTS grounds)")
            return License(permitted_modalities={Modality.REFUSAL})

        if any(g.strength == "strong" for g in factual_grounds):
            logger.debug("License (with links): ASSERTIVE, CONDITIONAL, REFUSAL (strong factual SUPPORTS)")
            return License(
                permitted_modalities={Modality.ASSERTIVE, Modality.CONDITIONAL, Modality.REFUSAL}
            )

        logger.debug("License (with links): CONDITIONAL, REFUSAL (weak factual SUPPORTS)")
        return License(permitted_modalities={Modality.CONDITIONAL, Modality.REFUSAL})

    def derive_with_trace(
        self, ground_set: GroundSet, links: Optional["LinkSet"] = None
    ) -> tuple[License, dict]:
        license = self.derive(ground_set, links=links)

        non_factual_scopes = sorted({k.scope.value for k in ground_set.nodes if k.scope != Scope.FACTUAL})

        trace: dict = {
            "mode": "links" if links is not None else "conservative",
            "ground_set_size": len(ground_set.nodes),
            "is_empty": ground_set.is_empty(),
            "factual": {
                "present": ground_set.has_scope(Scope.FACTUAL),
                "strength": ground_set.get_scope_strength(Scope.FACTUAL),
                "has_strong": ground_set.has_strong_in_scope(Scope.FACTUAL),
            },
            "non_factual_scopes_present": non_factual_scopes,
            "permitted_modalities": [m.value for m in license.permitted_modalities],
        }

        if links is not None:
            try:
                from ..models import LinkRole

                support_links = [link for link in links.links if link.role == LinkRole.SUPPORTS]
                trace["supports_links_count"] = len(support_links)
            except Exception:  # pragma: no cover
                trace["supports_links_count"] = None

        if ground_set.nodes:
            trace["nodes"] = [
                {
                    "id": k.id,
                    "scope": k.scope.value,
                    "strength": k.strength,
                }
                for k in ground_set.nodes
            ]

        return license, trace

