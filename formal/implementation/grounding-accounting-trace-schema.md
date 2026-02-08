# Trace Schema for FR-NORMCORE-IMPL-0001 (Grounding Accounting Model)

| Event | Actor | Inputs | Preconditions | Observable Outcome | TLA+ Action |
|-------|-------|--------|---------------|--------------------|-------------|
| ParseGroundsInput | `coerce_grounds_input` | `grounds` payload | Public API call with optional grounds | Payload accepted as internal `Ground` list or ignored as invalid | `TypeOK`, `ExternalGroundInputFeasible` |
| ParseOpenAIAnnotations | `coerce_grounds_input` + `parse_openai_citations` | OpenAI file/url annotations | Ground payload is OpenAI annotation array | External grounds accepted with canonical IDs (`file_id`/`url`) | `externalGroundsAccepted`, `externalGroundInputFormat` |
| BuildToolGroundRefs | `KnowledgeStateBuilder.build_with_references` + `grounds_from_tool_call_refs` | tool results with `tool_call_id` | Tool results extracted from conversation | Tool-based grounds accepted for citation keys | `toolGroundsAccepted` |
| MergeAcceptedGrounds | `AdmissibilityEvaluator.evaluate` | external grounds + tool grounds | Both sources available | `groundsAccepted` represents unique union of accepted grounds | `UnionCountFeasible` |
| BuildLinksFromCitations | `build_links_from_grounds` | assistant text with `[@key]` + accepted grounds | Citation keys found in assistant output | `groundsCited` bounded by accepted grounds | `InvCitedBounded` |
