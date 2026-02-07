# Draft vs Implementation: Semantic Delta

| Topic | Draft Model (`formal/draft`) | Implementation Model (`formal/implementation`) | Impact |
|------|------|------|------|
| Structural checks (F1/F2/F3) | Explicit first-class gate to `ILL_FORMED`. | Not explicitly evaluated in `_evaluate_core`; statements are constructed in normalized form. | Potential unreachable `ILL_FORMED` path in runtime core. |
| Status vocabulary | `ACCEPTABLE`, `CONDITIONALLY_ACCEPTABLE`, `VIOLATES_NORM`, `UNSUPPORTED`, `ILL_FORMED`, `UNDERDETERMINED`. | Adds `NO_NORMATIVE_CONTENT` precheck outcome. | Extra non-draft terminal state in production behavior. |
| Pre-evaluation gating | Draft algorithm starts with structure/modality/grounding determinability checks. | Adds empty-output and protocol-only gates before per-statement axioms. | Different early-exit behavior and observability. |
| Modality priority | REFUSAL > GOAL-CONDITIONAL > ASSERTIVE > CONDITIONAL > DESCRIPTIVE > ASSERTIVE(default). | Adds personalization-conditional override before recommendation assertive branch. | More conservative classification for personalization phrasing. |
| License derivation inputs | Table includes FACTUAL + CONTEXTUAL interplay. | Conservative mode uses factual strength only; links mode uses `SUPPORTS` links only. | Contextual weakening from draft is not currently active in runtime license derivation. |
| A7 conditional branch | `CONDITIONAL` with declared conditions => `CONDITIONALLY_ACCEPTABLE`. | `CONDITIONAL` becomes `CONDITIONALLY_ACCEPTABLE` if assertive license exists OR conditions declared. | Wider admissibility region for conditional statements in implementation. |
| Descriptive without factual ground | Falls through to `UNDERDETERMINED` in draft algorithm fallback. | Explicitly `UNSUPPORTED`. | Stricter runtime rejection for ungrounded descriptive claims. |
| UNDERDETERMINED triggers | Includes undetermined modality and ambiguous/incomplete grounding. | Explicitly covered for empty output; other cases mostly depend on residual branches. | Different interpretability for uncertainty states. |
| Aggregation semantics | Draft text describes single-statement algorithm. | Runtime performs lexicographic aggregation over statement results. | Multi-statement outcome rules are implementation-specific extension. |
| Link semantics | Not specified in draft. | Formalized statement-ground links with role filtering (`SUPPORTS` only for license). | New extension that changes licensing behavior under links mode. |

## Recommended Reconciliation Order

1. Decide whether contextual weakening from draft Table 5 should be restored in implementation or explicitly profiled out.
2. Decide normative status for ungrounded `DESCRIPTIVE` (`UNDERDETERMINED` vs `UNSUPPORTED`).
3. Decide whether A7 in implementation should require declared conditions when assertive license exists.
4. Decide if `NO_NORMATIVE_CONTENT` should be standardized as draft extension.
