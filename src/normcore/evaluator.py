"""
Admissibility Evaluator — deterministic axiom-based evaluation.

Evaluates agent speech acts for normative admissibility
according to the Normative Admissibility Framework.

This component applies a fixed set of normative axioms (A4–A7)
to determine whether a given agent statement is admissible
within a goal-directed activity.

CRITICAL DESIGN PRINCIPLES
--------------------------

1. Admissibility evaluation is NOT a numeric score.
   It is a judgment about the legitimacy of a speech act,
   not about semantic truth or task correctness.

2. Evaluation is FORM-based, not semantic.
   Decisions depend on:
   - statement modality (ASSERTIVE / CONDITIONAL / REFUSAL / DESCRIPTIVE)
   - available grounding (GroundSet)
   - axiomatically derived license

3. Aggregation is LEXICOGRAPHIC, not arithmetic.
   - A single VIOLATES_NORM outcome renders the entire speech act illegitimate.
   - Normative axioms are NOT additive.

4. UNDERDETERMINED denotes lack of evaluator jurisdiction.
   It is a valid outcome indicating that admissibility cannot be determined
   with the available information.

5. Numeric rewards, if present, exist ONLY for RL compatibility.
   They MUST NOT be interpreted as quality or performance signals.

GROUNDING AND CONTEXT
---------------------

- GroundSet is constructed exclusively from externally observable tool results.
- Personal or personalization context is treated as non-epistemic context:
  it MUST NOT contribute KnowledgeNodes or grant ASSERTIVE licenses.
- Personal context may influence modality framing (e.g. CONDITIONAL),
  but never grounding or license derivation.

OUTPUT
------

The evaluator produces a structured admissibility judgment, including:
- aggregated admissibility status
- licensing decision
- per-statement evaluation trace

The output is deterministic, auditable, and suitable for governance
and downstream policy enforcement.
"""

import json
from typing import TYPE_CHECKING, Any, Iterable, Optional, Union

from loguru import logger
from pydantic import ValidationError
from pydantic import TypeAdapter as _TypeAdapter  # pydantic v2

from .models.evaluator import (
    AdmissibilityJudgment,
    AdmissibilityStatus,
    GroundRef,
    StatementEvaluation,
)
from .models.messages import (
    RefusalSpeechAct,
    TextSpeechAct,
    ToolResultSpeechAct,
    _AssistantMessage,
    _ContentPart,
    _CustomToolCall,
    _FunctionMessage,
    _FunctionToolCall,
    _MappedMessage,
    _OtherMessage,
    _RefusalPart,
    _TextPart,
    _ToolCall,
    _ToolMessage,
)
from .citations import (
    build_links_from_grounds,
    coerce_grounds_input,
    grounds_from_tool_call_refs,
)
from .normative.axiom_checker import AxiomChecker
from .normative.models import (
    EvaluationStatus,
    KnowledgeNode,
    License,
    StatementValidationResult,
    ValidationResult,
)
from .normative.ground_matcher import GroundSetMatcher
from .normative.knowledge_builder import KnowledgeStateBuilder
from .normative.license_deriver import LicenseDeriver
from .normative.modality_detector import ModalityDetector
from .normative.statement_extractor import StatementExtractor

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnionParam,
    ChatCompletionToolMessageParam,
    ChatCompletionFunctionMessageParam,
)

if TYPE_CHECKING:
    from .citations import Ground

from .models import LinkSet

def _adapter(schema):
    """Create a pydantic TypeAdapter for the given schema."""
    return _TypeAdapter(schema)

class AdmissibilityEvaluator:
    """
    Evaluator implementing the Normative Admissibility Framework
    for agent speech acts.

    Evaluation flow:
    1. Collect externally observable tool results from the trajectory
    2. Construct GroundSet exclusively from those observations
    3. Extract normative speech acts from agent output
    4. For each speech act:
       a. Determine modality
       b. Match admissible grounding
       c. Derive permitted modalities (license)
       d. Evaluate admissibility via axioms
    5. Aggregate results into a single admissibility judgment
    """
    
    def __init__(self):
        """Initialize all components."""
        self.extractor = StatementExtractor()
        self.modality_detector = ModalityDetector()
        self.knowledge_builder = KnowledgeStateBuilder()
        self.ground_matcher = GroundSetMatcher()
        self.license_deriver = LicenseDeriver()
        self.axiom_checker = AxiomChecker()
        self._message_adapter = _adapter(ChatCompletionMessageParam)
        self._assistant_adapter = _adapter(ChatCompletionAssistantMessageParam)
        self._content_parts_adapter = _adapter(list[_ContentPart])
    
    @classmethod
    def evaluate(
        cls,
        agent_message: ChatCompletionAssistantMessageParam,
        trajectory: list[ChatCompletionMessageParam],
        personal_context: Optional[str] = None,
        personal_context_scope: str = "unknown",
        personal_context_source: str = "unknown",
        grounds: Optional[list['Ground']] = None,
        **kwargs: Any,
    ) -> AdmissibilityJudgment:
        """
        Runtime evaluation of an agent message (speech act).
        
        Used in orchestrator to check public speech acts before accepting them.
        
        Args:
            agent_message: Single agent message to validate
            trajectory: Full message history (for building knowledge state)
            personal_context: Optional non-epistemic personalization context (YAML/JSON string)
            personal_context_scope: "global" | "session" | "unknown"
            personal_context_source: "user" | "system" | "memory" | "unknown"
            grounds: Optional grounds input (citation_key -> ground_id)
            **kwargs: Additional args (for compatibility)
        
        Returns:
            AdmissibilityJudgment with status and retry guidance for agent
        """
        instance = cls()
        
        # 1. Extract tool results from trajectory
        tool_results = instance._extract_tool_results(trajectory)
        
        # 2. Build knowledge state + tool-call reference grounds
        knowledge_nodes, tool_call_refs = instance.knowledge_builder.build_with_references(tool_results)

        # 3. Validate + map and get agent output
        validated_agent_message = instance._assistant_adapter.validate_python(agent_message)
        # AFTER THIS POINT: no OpenAI types allowed
        assistant_message = instance._map_assistant_message(validated_agent_message)
        speech_act = instance._to_speech_act(assistant_message)

        provided_grounds = coerce_grounds_input(
            grounds=grounds,
            legacy_openai_citations=kwargs.get("openai_citations"),
            legacy_links=kwargs.get("links"),
        )
        knowledge_nodes = instance.knowledge_builder.materialize_external_grounds(
            knowledge_nodes,
            provided_grounds,
        )
        combined_grounds = [*provided_grounds, *grounds_from_tool_call_refs(tool_call_refs)]

        statement_id = "refusal" if isinstance(speech_act, RefusalSpeechAct) else "final_response"
        text = speech_act.refusal if isinstance(speech_act, RefusalSpeechAct) else speech_act.text
        links = build_links_from_grounds(
            text=text,
            grounds=combined_grounds,
            statement_id=statement_id,
        )
        accepted_ground_ids = {ground.ground_id for ground in combined_grounds}
        cited_ground_ids = {link.ground_id for link in links.links}

        if isinstance(speech_act, RefusalSpeechAct):
            internal_result = instance._evaluate_refusal(
                speech_act.refusal,
                knowledge_nodes,
                links,
                personal_context=personal_context,
                personal_context_scope=personal_context_scope,
                personal_context_source=personal_context_source,
            )
            internal_result.grounds_accepted = len(accepted_ground_ids)
            internal_result.grounds_cited = len(cited_ground_ids)
            return instance._to_judgment(internal_result)
        agent_output = speech_act.text
        
        # 4. Run evaluation core
        internal_result = instance._evaluate_core(
            agent_output=agent_output,
            knowledge_nodes=knowledge_nodes,
            links=links,
            personal_context=personal_context,
            personal_context_scope=personal_context_scope,
            personal_context_source=personal_context_source,
        )
        internal_result.grounds_accepted = len(accepted_ground_ids)
        internal_result.grounds_cited = len(cited_ground_ids)
        return instance._to_judgment(internal_result)

    def _evaluate_core(
        self,
        agent_output: str,
        knowledge_nodes: list[KnowledgeNode],
        links: Optional['LinkSet'],
        personal_context: Optional[str],
        personal_context_scope: str,
        personal_context_source: str,
    ) -> ValidationResult:
        """
        Evaluation core. All normative checking happens here.
        
        Flow:
        1. Extract statements from agent output
        2. For each statement:
           a. Detect modality
           b. Match grounds
           c. Derive license
           d. Check axioms
        3. Aggregate → ValidationResult
        
        NEW v0.3.1:
        links parameter enables usage-based licensing:
        - If links provided → usage-based mode (only SUPPORTS links)
        - If None → v0.2 conservative mode (presence = usage)
        
        Args:
            agent_output: Text to validate
            knowledge_nodes: Already built knowledge state
            links: Optional StatementGroundLinks
            personal_context: Optional non-epistemic personalization context (YAML/JSON string)
            personal_context_scope: "global" | "session" | "unknown"
            personal_context_source: "user" | "system" | "memory" | "unknown"
        
        Returns:
            ValidationResult with status, feedback_hint, violations
        """
        # 1. Extract statements
        if not agent_output:
            return ValidationResult(
                status=EvaluationStatus.UNDERDETERMINED,
                licensed=False,
                can_retry=False,
                explanation="No content to validate",
                personal_context_source=personal_context_source,
                personal_context_scope=personal_context_scope,
                personal_context_present=bool(personal_context),
            )
        
        statements = self.extractor.extract(agent_output)
        
        if not statements:
            # NEW v0.2.1: NO_NORMATIVE_CONTENT (per FORMAL_SPEC_v0.2.1 §0.4.5)
            # 
            # Speech Act Segmentation Layer (§0.4) produced zero normative utterances.
            # This means agent output contained ONLY protocol speech (greetings, offers).
            # 
            # This is NOT UNDERDETERMINED (cannot judge).
            # This is NO JURISDICTION (protocol-only output, no claims to evaluate).
            # 
            # Per §0.4.5:
            # "NO_NORMATIVE_CONTENT is a pre-evaluation filter result indicating
            #  evaluator has no jurisdiction to judge (protocol-only output)."
            # 
            # Examples triggering this:
            # - "Hello! I'm ready to help."
            # - "Good morning! What can I do for you?"
            # - "I'm doing well, thanks. How can I assist?"
            # 
            # After segmentation (stripping protocol speech), nothing remains.
            # No normative claims made → no axioms apply → no evaluation performed.
            logger.info(
                "AdmissibilityEvaluator: No normative utterances extracted "
                "(protocol-only output after segmentation)"
            )
            return ValidationResult(
                status=EvaluationStatus.NO_NORMATIVE_CONTENT,
                licensed=False,  # Not licensed (no normative claim to license)
                can_retry=False,  # Not a failure (protocol speech is acceptable)
                explanation="Protocol-only output (greetings/offers) - no normative claims to evaluate",
                personal_context_source=personal_context_source,
                personal_context_scope=personal_context_scope,
                personal_context_present=bool(personal_context),
            )
        
        logger.info(f"AdmissibilityEvaluator: Extracted {len(statements)} statements")
        
        # 2. Validate each statement
        statement_results = []
        axiom_results = []
        
        from .normative.models import Modality
        
        for statement in statements:
            # Detect modality and extract conditions
            self.modality_detector.detect_with_conditions(statement)
            
            # Find relevant grounds
            ground_set = self.ground_matcher.match(statement, knowledge_nodes)
            
            # Derive license (ONLY for normative modalities)
            # CRITICAL v0.2: DESCRIPTIVE does not require licensing
            # Skip license derivation for DESCRIPTIVE, pass empty license to axiom checker
            # NEW v0.3.1: Pass links for usage-based licensing (if available)
            if statement.modality == Modality.DESCRIPTIVE:
                # DESCRIPTIVE statements evaluated directly by AxiomChecker
                # No license needed (factual observation, not normative claim)
                license = License(permitted_modalities=set())
            else:
                # ASSERTIVE/CONDITIONAL/REFUSAL require licensing
                # v0.3.1: Pass links for usage-based mode (if available)
                license = self.license_deriver.derive(ground_set, links=links)
            
            # Check axioms
            result = self.axiom_checker.check(
                statement,
                license,
                ground_set,
                task_goal="task completion",
            )
            axiom_results.append(result)
            
            # Build detailed statement result
            stmt_result = StatementValidationResult(
                statement=statement,
                status=result.status,
                license=license,
                ground_set=ground_set,
                violated_axiom=result.violated_axiom,
                explanation=result.explanation,
            )
            statement_results.append(stmt_result)
            
            # Log evaluation
            logger.info(f"  Statement: {statement.raw_text[:80]}...")
            logger.info(
                f"    Modality: {statement.modality.value}, "
                f"License: {[m.value for m in license.permitted_modalities]}, "
                f"Status: {result.status.value}"
            )
            if result.violated_axiom:
                logger.info(f"    Violated: {result.violated_axiom}")
        
        # 3. Aggregate to ValidationResult (lexicographic logic)
        return self._aggregate(
            axiom_results,
            statement_results,
            personal_context=personal_context,
            personal_context_scope=personal_context_scope,
            personal_context_source=personal_context_source,
        )
    
    def _aggregate(
        self,
        axiom_results: list,
        statement_results: list[StatementValidationResult],
        personal_context: Optional[str],
        personal_context_scope: str,
        personal_context_source: str,
    ) -> ValidationResult:
        """
        Aggregate axiom check results to ValidationResult.
        
        Normative aggregation (per LOGICAL_DAG_SPEC v0.1):
        1. if any(VIOLATES_NORM): FAIL (reward=0.0)
        2. elif any(ILL_FORMED): FAIL (reward=0.0)
        3. elif any(UNDERDETERMINED): EVAL_NOT_LICENSED (reward=1.0 NEUTRAL)
        4. elif any(UNSUPPORTED): PARTIAL (reward=0.0)
        5. elif any(CONDITIONALLY_ACCEPTABLE): CONDITIONAL (reward=0.8-0.9)
        6. else: ACCEPTABLE (reward=1.0)
        
        One illegitimate statement makes the entire act illegitimate.
        Normative axioms are NOT additive.
        
        CRITICAL: UNDERDETERMINED means:
        - Evaluator has no jurisdiction to judge
        - This is NOT a reward for good performance
        - This is a NEUTRAL pass-through (no training signal)
        - Prevents RL from optimizing "say things evaluator cannot judge"
        
        Returns ValidationResult with status, feedback_hint, violations.
        """
        violations = [r.violated_axiom for r in axiom_results if r.violated_axiom]
        
        # Lexicographic aggregation
        if any(r.status == EvaluationStatus.VIOLATES_NORM for r in axiom_results):
            status = EvaluationStatus.VIOLATES_NORM
            licensed = False
            can_retry = True
            feedback_hint = (
                f"Your response violates normative axioms: {', '.join(violations)}. "
                f"Please revise or refuse to answer if you lack required context."
            )
            explanation = f"Violated axioms: {violations}"
        
        elif any(r.status == EvaluationStatus.ILL_FORMED for r in axiom_results):
            status = EvaluationStatus.ILL_FORMED
            licensed = False
            can_retry = True
            feedback_hint = (
                "Your response is structurally ill-formed. "
                "Please rephrase with clear subject-predicate statements."
            )
            explanation = "Structurally ill-formed statements detected"
        
        elif any(r.status == EvaluationStatus.UNDERDETERMINED for r in axiom_results):
            status = EvaluationStatus.UNDERDETERMINED
            licensed = False
            can_retry = False
            feedback_hint = None  # Validator has no jurisdiction
            explanation = "Validator has no jurisdiction to judge"
        
        elif any(r.status == EvaluationStatus.UNSUPPORTED for r in axiom_results):
            status = EvaluationStatus.UNSUPPORTED
            licensed = True
            can_retry = True
            feedback_hint = (
                "Your statements lack required grounding. "
                "Consider asking for more context or using conditional phrasing."
            )
            explanation = "Statements lack required grounding (A4)"
        
        elif all(r.status == EvaluationStatus.CONDITIONALLY_ACCEPTABLE for r in axiom_results):
            status = EvaluationStatus.CONDITIONALLY_ACCEPTABLE
            licensed = True
            can_retry = False
            feedback_hint = None
            explanation = "All statements are conditionally acceptable"
        
        elif any(r.status == EvaluationStatus.CONDITIONALLY_ACCEPTABLE for r in axiom_results):
            status = EvaluationStatus.CONDITIONALLY_ACCEPTABLE
            licensed = True
            can_retry = False
            feedback_hint = None
            explanation = "Mix of conditional and acceptable statements"
        
        else:
            # All ACCEPTABLE
            status = EvaluationStatus.ACCEPTABLE
            licensed = True
            can_retry = False
            feedback_hint = None
            explanation = "All statements are normatively acceptable"
        
        num_acceptable = sum(
            1 for r in axiom_results 
            if r.status in {EvaluationStatus.ACCEPTABLE, EvaluationStatus.CONDITIONALLY_ACCEPTABLE}
        )
        
        logger.info(
            f"AdmissibilityEvaluator: Status={status.value}, Licensed={licensed}, "
            f"({num_acceptable}/{len(statement_results)} acceptable, {len(violations)} violations)"
        )
        
        return ValidationResult(
            status=status,
            licensed=licensed,
            can_retry=can_retry,
            feedback_hint=feedback_hint,
            violated_axioms=violations,
            statement_results=statement_results,
            explanation=explanation,
            num_statements=len(statement_results),
            num_acceptable=num_acceptable,
            personal_context_source=personal_context_source,
            personal_context_scope=personal_context_scope,
            personal_context_present=bool(personal_context),
        )

    @staticmethod
    def _to_judgment(result: ValidationResult) -> AdmissibilityJudgment:
        """
        Convert internal ValidationResult into public AdmissibilityJudgment.

        Public model is stable, minimal, and audited.
        """
        def _status(s: EvaluationStatus) -> AdmissibilityStatus:
            try:
                return AdmissibilityStatus(s.value)
            except ValueError:
                return AdmissibilityStatus.UNDERDETERMINED

        statement_evaluations: list[StatementEvaluation] = []
        violated_axioms: list[str] = []

        for stmt in result.statement_results:
            modality = stmt.statement.modality.value if stmt.statement.modality else "unknown"
            permitted = {m.value for m in stmt.license.permitted_modalities}

            grounding_trace = [
                GroundRef(
                    id=k.id,
                    scope=k.scope.value,
                    source=k.source.value,
                    status=k.status.value,
                    confidence=k.confidence,
                    strength=k.strength,
                    semantic_id=k.semantic_id,
                )
                for k in stmt.ground_set.nodes
            ]

            statement_evaluations.append(
                StatementEvaluation(
                    statement_id=stmt.statement.id,
                    statement=stmt.statement.raw_text,
                    modality=modality,
                    license=permitted,
                    status=_status(stmt.status),
                    violated_axiom=stmt.violated_axiom,
                    explanation=stmt.explanation,
                    grounding_trace=grounding_trace,
                    subject=stmt.statement.subject,
                    predicate=stmt.statement.predicate,
                )
            )
            if stmt.violated_axiom:
                violated_axioms.append(stmt.violated_axiom)

        return AdmissibilityJudgment(
            status=_status(result.status),
            licensed=result.licensed,
            can_retry=result.can_retry,
            statement_evaluations=statement_evaluations,
            feedback_hint=result.feedback_hint,
            violated_axioms=violated_axioms,
            explanation=result.explanation,
            num_statements=result.num_statements,
            num_acceptable=result.num_acceptable,
            personal_context_source=result.personal_context_source,
            personal_context_scope=result.personal_context_scope,
            personal_context_present=result.personal_context_present,
            grounds_accepted=result.grounds_accepted,
            grounds_cited=result.grounds_cited,
        )
    
    def _extract_tool_results(
        self,
        trajectory: list[ChatCompletionMessageParam],
    ) -> list[ToolResultSpeechAct]:
        """
        Extract tool call results from trajectory.
        
        Tool results can appear in two forms:
        1. In tool_calls with embedded results (newer format)
        2. As separate messages with role='tool' (older/current format)
        
        Args:
            trajectory: List of messages
        
        Returns:
            List of ToolResultSpeechAct
        """
        tool_results = []
        
        tool_call_by_id: dict[str, dict] = {}
        for message in trajectory:
            validated_message = self._validate_message(message)
            mapped_message = self._map_message(validated_message)
            if not isinstance(mapped_message, _AssistantMessage):
                continue
            for tool_call in mapped_message.tool_calls:
                if isinstance(tool_call, _FunctionToolCall):
                    args = self._parse_tool_args(tool_call.arguments)
                    tool_call_by_id[tool_call.id] = {
                        "name": tool_call.name,
                        "arguments": args,
                    }
        
        # Method 2: Extract from separate tool messages (role='tool')
        for message in trajectory:
            validated_message = self._validate_message(message)
            mapped_message = self._map_message(validated_message)
            if isinstance(mapped_message, _ToolMessage):
                call_meta = tool_call_by_id.get(mapped_message.tool_call_id, {})
                content = self._extract_text_content(mapped_message.content)
                tool_results.append(ToolResultSpeechAct(
                    tool_name=call_meta.get("name", "unknown"),
                    tool_call_id=mapped_message.tool_call_id,
                    arguments=call_meta.get("arguments", {}),
                    result_text=content,
                ))
            elif isinstance(mapped_message, _FunctionMessage):
                if mapped_message.name:
                    content = self._extract_text_content(mapped_message.content)
                    tool_results.append(ToolResultSpeechAct(
                        tool_name=mapped_message.name,
                        result_text=content,
                    ))
        
        return tool_results
    
    @staticmethod
    def _extract_text_content(content: Union[str, list["_ContentPart"], None]) -> str:
        """Normalize message content into a plain text string."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(p.text for p in content if isinstance(p, _TextPart)).strip()
        raise ValueError(f"Unsupported content type: {type(content)}")

    @staticmethod
    def _parse_tool_args(arguments: Any) -> dict:
        """Parse tool call arguments into a dict, handling JSON strings."""
        if arguments is None:
            return {}
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str):
            try:
                return json.loads(arguments)
            except json.JSONDecodeError:
                return {}
        return {}

    def _validate_message(self, message: ChatCompletionMessageParam) -> ChatCompletionMessageParam:
        """Validate a raw message against the OpenAI message schema."""
        try:
            return self._message_adapter.validate_python(message)
        except ValidationError as exc:  # pragma: no cover
            raise ValueError(f"Invalid OpenAI ChatCompletionMessageParam: {exc}") from exc

    def _map_message(self, message: ChatCompletionMessageParam) -> "_MappedMessage":
        """Map a validated message into an internal message model."""
        role = message["role"]
        if role == "assistant":
            return self._map_assistant_message(message)
        if role == "tool":
            return self._map_tool_message(message)
        if role == "function":
            return self._map_function_message(message)
        return _OtherMessage(role=role)

    def _map_assistant_message(self, message: ChatCompletionAssistantMessageParam) -> "_AssistantMessage":
        """Convert assistant message into internal assistant model."""
        content = self._map_content(message["content"] if "content" in message else None)
        tool_calls = []
        for tool_call in (message["tool_calls"] if "tool_calls" in message else []):
            tool_calls.append(self._map_tool_call(tool_call))
        return _AssistantMessage(content=content, tool_calls=tool_calls)

    def _map_tool_message(self, message: ChatCompletionToolMessageParam) -> "_ToolMessage":
        """Convert tool message into internal tool model."""
        content = self._map_content(message["content"])
        if any(isinstance(p, _RefusalPart) for p in (content or [])):
            raise ValueError("Tool message content cannot include refusal parts")
        return _ToolMessage(tool_call_id=message["tool_call_id"], content=content)

    def _map_function_message(self, message: ChatCompletionFunctionMessageParam) -> "_FunctionMessage":
        """Convert function message into internal function model."""
        content = self._map_content(message["content"])
        return _FunctionMessage(name=message["name"], content=content)

    def _map_content(self, content: Any) -> Union[str, list["_ContentPart"], None]:
        """Validate and normalize message content into internal parts."""
        if content is None:
            return None
        if isinstance(content, str):
            return content
        if isinstance(content, Iterable):
            return self._content_parts_adapter.validate_python(content)
        raise ValueError(f"Unsupported content type: {type(content)}")

    def _map_tool_call(self, tool_call: ChatCompletionMessageToolCallUnionParam) -> "_ToolCall":
        """Convert a tool call into its internal representation."""
        if tool_call["type"] == "function":
            fn = tool_call["function"]
            return _FunctionToolCall(
                id=tool_call["id"],
                name=fn["name"],
                arguments=fn["arguments"],
            )
        if tool_call["type"] == "custom":
            custom = tool_call["custom"]
            return _CustomToolCall(
                id=tool_call["id"],
                name=custom["name"],
                input_value=custom["input"],
            )
        raise ValueError(f"Unsupported tool call type: {tool_call['type']}")

    def _to_speech_act(self, assistant_message: _AssistantMessage) -> TextSpeechAct | RefusalSpeechAct:
        """Convert assistant message content into a text or refusal speech act."""
        content = assistant_message.content
        if content is None:
            return TextSpeechAct(text="")
        if isinstance(content, str):
            return TextSpeechAct(text=content)
        if isinstance(content, list):
            refusal_parts = [p.refusal for p in content if isinstance(p, _RefusalPart)]
            text_parts = [p.text for p in content if isinstance(p, _TextPart)]
            if refusal_parts and text_parts:
                raise ValueError("Assistant content cannot mix text and refusal parts")
            if refusal_parts:
                return RefusalSpeechAct(refusal="".join(refusal_parts).strip())
            return TextSpeechAct(text="".join(text_parts).strip())
        raise ValueError(f"Unsupported assistant content type: {type(content)}")

    def _evaluate_refusal(
        self,
        refusal_text: str,
        knowledge_nodes: list[KnowledgeNode],
        links: Optional['LinkSet'],
        personal_context: Optional[str],
        personal_context_scope: str,
        personal_context_source: str,
    ) -> ValidationResult:
        """Evaluate a refusal speech act using the same axioms."""
        from .normative.models import Modality, Statement
        statement = Statement(
            id="refusal",
            subject="agent",
            predicate="refuses",
            raw_text=refusal_text,
            modality=Modality.REFUSAL,
            conditions=[],
        )
        ground_set = self.ground_matcher.match(statement, knowledge_nodes)
        license = self.license_deriver.derive(ground_set, links=links)
        result = self.axiom_checker.check(
            statement,
            license,
            ground_set,
            task_goal="task completion",
        )
        stmt_result = StatementValidationResult(
            statement=statement,
            status=result.status,
            license=license,
            ground_set=ground_set,
            violated_axiom=result.violated_axiom,
            explanation=result.explanation,
        )
        return self._aggregate(
            [result],
            [stmt_result],
            personal_context=personal_context,
            personal_context_scope=personal_context_scope,
            personal_context_source=personal_context_source,
        )
