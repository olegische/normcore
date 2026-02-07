# ChatGPT Feedback Resolution (Draft Model)

Source reviewed: user-provided feedback on `formal/draft/spec.tla`.

| Feedback Point | Resolution | Action |
|---|---|---|
| 1. `InvContextualWeakening` is normatively paradoxical (`contextual=none` vs `weak`) | The model currently mirrors Draft Table 5 exactly; asymmetry is in source text, not in TLA encoding. | Kept semantics unchanged; logged as `D-OQ-004` in `open-formalization-questions.md`. |
| 2. `DESCRIPTIVE` branch should always be `ACCEPTABLE` | Draft algorithm only states grounded descriptive acceptance explicitly; ungrounded case falls to default `UNDERDETERMINED`. | Kept semantics unchanged; made it explicit via `InvDescriptiveUngroundedFallsToUnderdetermined` and property `D-DESCRIPTIVE-UNGROUNDED-FALLBACK`. |
| 3. A7 is too weak (only `conditionsDeclared`) | This is a valid critique of draft semantics, but the reference draft model must preserve source algorithm and branch order. | Kept semantics unchanged; logged as `D-OQ-005`. |
| 4. `UNSUPPORTED` vs `VIOLATES_NORM` priority should change | Draft §7.5 orders A5 before A4; assertive-empty-ground therefore resolves through A5 first. | Kept semantics unchanged; added invariant `InvA5BeforeA4ForAssertiveEmptyGround`. |
| 5. `EvalStatus` total deterministic classifier is good | Agreed; this is intended architecture for derivation model. | Added explicit invariant `InvTotalFunction`. |
| 6. Missing invariants on totality and license consistency | Agreed. | Added `InvTotalFunction` and `InvAcceptableAssertiveLicensed` and wired them in `spec.cfg`. |

## Net Result

The draft model is now stricter as a reference artifact (explicitly asserts controversial branches) without silently rewriting draft semantics.
