use crate::citations::build_links_from_grounds;
use crate::citations::coerce_grounds_input;
use crate::citations::grounds_from_tool_call_refs;
use crate::json::JsonValue;
use crate::json::parse_json;
use crate::models::AdmissibilityJudgment;
use crate::models::AdmissibilityStatus;
use crate::models::ConversationMessage;
use crate::models::Ground;
use crate::models::GroundRef;
use crate::models::LinkSet;
use crate::models::StatementEvaluation;
use crate::models::TextSpeechAct;
use crate::models::ToolCall;
use crate::models::ToolResultSpeechAct;
use crate::normative::AxiomChecker;
use crate::normative::EvaluationStatus;
use crate::normative::GroundSetMatcher;
use crate::normative::KnowledgeNode;
use crate::normative::KnowledgeStateBuilder;
use crate::normative::License;
use crate::normative::LicenseDeriver;
use crate::normative::Modality;
use crate::normative::ModalityDetector;
use crate::normative::StatementExtractor;
use crate::normative::StatementValidationResult;
use crate::normative::ValidationResult;
use std::collections::BTreeMap;
use std::collections::BTreeSet;

#[derive(Debug, Clone, PartialEq)]
pub struct EvaluateInput {
    pub agent_output: Option<String>,
    pub conversation: Option<Vec<ConversationMessage>>,
    pub grounds: Option<Vec<Ground>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvaluateError {
    MissingInput,
    InvalidConversation,
    LastMessageNotAssistant,
    LastAssistantContentNotString,
    AgentOutputMismatch,
    InvalidJson(String),
    InvalidMessage(String),
}

pub fn evaluate(input: EvaluateInput) -> Result<AdmissibilityJudgment, EvaluateError> {
    if input.agent_output.is_none() && input.conversation.is_none() {
        return Err(EvaluateError::MissingInput);
    }

    let (agent_message, trajectory): (ConversationMessage, Vec<ConversationMessage>) =
        if let Some(conversation) = input.conversation.clone() {
            if conversation.is_empty() {
                return Err(EvaluateError::InvalidConversation);
            }
            let last = conversation
                .last()
                .cloned()
                .ok_or(EvaluateError::InvalidConversation)?;
            if last.role != "assistant" {
                return Err(EvaluateError::LastMessageNotAssistant);
            }

            if let Some(expected_output) = &input.agent_output {
                let actual = extract_text_content(last.content.as_ref())?;
                if &actual != expected_output {
                    return Err(EvaluateError::AgentOutputMismatch);
                }
            }

            (last, conversation)
        } else {
            let msg = ConversationMessage {
                role: "assistant".to_string(),
                content: Some(JsonValue::String(
                    input.agent_output.clone().unwrap_or_default(),
                )),
                tool_call_id: None,
                tool_calls: Vec::new(),
                function_name: None,
            };
            (msg.clone(), vec![msg])
        };

    let evaluator = AdmissibilityEvaluator::new();
    evaluator.evaluate_message(
        &agent_message,
        &trajectory,
        input.grounds.unwrap_or_default(),
    )
}

pub fn evaluate_from_json(input: &str) -> Result<AdmissibilityJudgment, EvaluateError> {
    let value = parse_json(input).map_err(|e| EvaluateError::InvalidJson(e.message))?;
    let obj = value
        .as_object()
        .ok_or_else(|| EvaluateError::InvalidJson("payload must be object".to_string()))?;

    let agent_output = obj
        .get("agent_output")
        .and_then(JsonValue::as_str)
        .map(ToString::to_string);

    let conversation = match obj.get("conversation") {
        Some(JsonValue::Array(arr)) => Some(parse_conversation(arr)?),
        Some(JsonValue::Null) | None => None,
        _ => {
            return Err(EvaluateError::InvalidJson(
                "conversation must be an array".to_string(),
            ));
        }
    };

    let grounds = match obj.get("grounds") {
        Some(JsonValue::Array(arr)) => Some(coerce_grounds_input(Some(arr), None, None)),
        Some(JsonValue::Null) | None => None,
        _ => {
            return Err(EvaluateError::InvalidJson(
                "grounds must be an array".to_string(),
            ));
        }
    };

    evaluate(EvaluateInput {
        agent_output,
        conversation,
        grounds,
    })
}

pub fn parse_conversation(
    messages: &[JsonValue],
) -> Result<Vec<ConversationMessage>, EvaluateError> {
    let mut out = Vec::new();
    for msg in messages {
        let obj = msg
            .as_object()
            .ok_or_else(|| EvaluateError::InvalidMessage("message must be object".to_string()))?;
        let role = obj
            .get("role")
            .and_then(JsonValue::as_str)
            .ok_or_else(|| EvaluateError::InvalidMessage("message.role is required".to_string()))?
            .to_string();

        let content = obj.get("content").cloned();

        let tool_call_id = obj
            .get("tool_call_id")
            .and_then(JsonValue::as_str)
            .map(ToString::to_string);

        let function_name = obj
            .get("name")
            .and_then(JsonValue::as_str)
            .map(ToString::to_string);

        let tool_calls = parse_tool_calls(obj.get("tool_calls"))?;

        out.push(ConversationMessage {
            role,
            content,
            tool_call_id,
            tool_calls,
            function_name,
        });
    }
    Ok(out)
}

fn parse_tool_calls(value: Option<&JsonValue>) -> Result<Vec<ToolCall>, EvaluateError> {
    let Some(value) = value else {
        return Ok(Vec::new());
    };
    let Some(arr) = value.as_array() else {
        return Err(EvaluateError::InvalidMessage(
            "tool_calls must be an array".to_string(),
        ));
    };

    let mut out = Vec::new();
    for item in arr {
        let Some(obj) = item.as_object() else {
            continue;
        };
        let Some(id) = obj.get("id").and_then(JsonValue::as_str) else {
            continue;
        };
        let kind = obj
            .get("type")
            .and_then(JsonValue::as_str)
            .unwrap_or("function")
            .to_string();

        let mut function_name = None;
        let mut function_arguments = None;
        if let Some(function_obj) = obj.get("function").and_then(JsonValue::as_object) {
            function_name = function_obj
                .get("name")
                .and_then(JsonValue::as_str)
                .map(ToString::to_string);
            function_arguments = function_obj.get("arguments").cloned();
        }

        let mut custom_name = None;
        let mut custom_input = None;
        if let Some(custom_obj) = obj.get("custom").and_then(JsonValue::as_object) {
            custom_name = custom_obj
                .get("name")
                .and_then(JsonValue::as_str)
                .map(ToString::to_string);
            custom_input = custom_obj
                .get("input")
                .and_then(JsonValue::as_str)
                .map(ToString::to_string);
        }

        out.push(ToolCall {
            id: id.to_string(),
            kind,
            function_name,
            function_arguments,
            custom_name,
            custom_input,
        });
    }

    Ok(out)
}

pub struct AdmissibilityEvaluator {
    extractor: StatementExtractor,
    modality_detector: ModalityDetector,
    knowledge_builder: KnowledgeStateBuilder,
    ground_matcher: GroundSetMatcher,
    license_deriver: LicenseDeriver,
    axiom_checker: AxiomChecker,
}

impl Default for AdmissibilityEvaluator {
    fn default() -> Self {
        Self::new()
    }
}

impl AdmissibilityEvaluator {
    pub fn new() -> Self {
        Self {
            extractor: StatementExtractor,
            modality_detector: ModalityDetector,
            knowledge_builder: KnowledgeStateBuilder,
            ground_matcher: GroundSetMatcher,
            license_deriver: LicenseDeriver,
            axiom_checker: AxiomChecker,
        }
    }

    pub fn evaluate_message(
        &self,
        agent_message: &ConversationMessage,
        trajectory: &[ConversationMessage],
        grounds: Vec<Ground>,
    ) -> Result<AdmissibilityJudgment, EvaluateError> {
        let tool_results = self.extract_tool_results(trajectory)?;
        let (mut knowledge_nodes, tool_call_refs) =
            self.knowledge_builder.build_with_references(&tool_results);

        let speech_act = self.to_speech_act(agent_message)?;

        knowledge_nodes = self
            .knowledge_builder
            .materialize_external_grounds(&knowledge_nodes, &grounds);

        let mut combined_grounds = grounds;
        combined_grounds.extend(grounds_from_tool_call_refs(&tool_call_refs));

        let statement_id = "final_response";
        let text = speech_act.text;

        let links = build_links_from_grounds(&text, &combined_grounds, statement_id);
        let accepted_ground_ids: BTreeSet<String> = combined_grounds
            .iter()
            .map(|ground| ground.ground_id.clone())
            .collect();
        let cited_ground_ids: BTreeSet<String> = links
            .links
            .iter()
            .map(|link| link.ground_id.clone())
            .collect();

        let mut internal_result = self.evaluate_core(&text, &knowledge_nodes, Some(&links));
        internal_result.grounds_accepted = accepted_ground_ids.len();
        internal_result.grounds_cited = cited_ground_ids.len();

        Ok(self.to_judgment(internal_result))
    }

    pub fn evaluate_core(
        &self,
        agent_output: &str,
        knowledge_nodes: &[KnowledgeNode],
        links: Option<&LinkSet>,
    ) -> ValidationResult {
        if agent_output.is_empty() {
            return ValidationResult {
                status: EvaluationStatus::Underdetermined,
                licensed: false,
                can_retry: false,
                feedback_hint: None,
                violated_axioms: vec![],
                statement_results: vec![],
                explanation: "No content to validate".to_string(),
                num_statements: 0,
                num_acceptable: 0,
                grounds_accepted: 0,
                grounds_cited: 0,
            };
        }

        let mut statements = self.extractor.extract(agent_output);
        if statements.is_empty() {
            return ValidationResult {
                status: EvaluationStatus::NoNormativeContent,
                licensed: false,
                can_retry: false,
                feedback_hint: None,
                violated_axioms: vec![],
                statement_results: vec![],
                explanation:
                    "Protocol-only output (greetings/offers) - no normative claims to evaluate"
                        .to_string(),
                num_statements: 0,
                num_acceptable: 0,
                grounds_accepted: 0,
                grounds_cited: 0,
            };
        }

        let mut statement_results = Vec::new();
        let mut axiom_results = Vec::new();

        for statement in &mut statements {
            self.modality_detector.detect_with_conditions(statement);
            let ground_set = self.ground_matcher.match_nodes(statement, knowledge_nodes);

            let license = if statement.modality == Some(Modality::Descriptive) {
                License {
                    permitted_modalities: BTreeSet::new(),
                }
            } else {
                self.license_deriver.derive(&ground_set, links)
            };

            let result =
                self.axiom_checker
                    .check(statement, &license, &ground_set, "task completion");
            axiom_results.push(result.clone());

            statement_results.push(StatementValidationResult {
                statement: statement.clone(),
                status: result.status,
                license,
                ground_set,
                violated_axiom: result.violated_axiom,
                explanation: result.explanation,
            });
        }

        self.aggregate(&axiom_results, &statement_results)
    }

    fn aggregate(
        &self,
        axiom_results: &[crate::normative::AxiomCheckResult],
        statement_results: &[StatementValidationResult],
    ) -> ValidationResult {
        let violations: Vec<String> = axiom_results
            .iter()
            .filter_map(|r| r.violated_axiom.clone())
            .collect();

        let (status, licensed, can_retry, feedback_hint, explanation) = if axiom_results
            .iter()
            .any(|r| r.status == EvaluationStatus::ViolatesNorm)
        {
            (
                EvaluationStatus::ViolatesNorm,
                false,
                true,
                Some(format!(
                    "Your response violates normative axioms: {}. Please revise or refuse to answer if you lack required context.",
                    violations.join(", ")
                )),
                format!("Violated axioms: {violations:?}"),
            )
        } else if axiom_results
            .iter()
            .any(|r| r.status == EvaluationStatus::IllFormed)
        {
            (
                EvaluationStatus::IllFormed,
                false,
                true,
                Some(
                    "Your response is structurally ill-formed. Please rephrase with clear subject-predicate statements."
                        .to_string(),
                ),
                "Structurally ill-formed statements detected".to_string(),
            )
        } else if axiom_results
            .iter()
            .any(|r| r.status == EvaluationStatus::Underdetermined)
        {
            (
                EvaluationStatus::Underdetermined,
                false,
                false,
                None,
                "Validator has no jurisdiction to judge".to_string(),
            )
        } else if axiom_results
            .iter()
            .any(|r| r.status == EvaluationStatus::Unsupported)
        {
            (
                EvaluationStatus::Unsupported,
                true,
                true,
                Some(
                    "Your statements lack required grounding. Consider asking for more context or using conditional phrasing."
                        .to_string(),
                ),
                "Statements lack required grounding (A4)".to_string(),
            )
        } else if !axiom_results.is_empty()
            && axiom_results
                .iter()
                .all(|r| r.status == EvaluationStatus::ConditionallyAcceptable)
        {
            (
                EvaluationStatus::ConditionallyAcceptable,
                true,
                false,
                None,
                "All statements are conditionally acceptable".to_string(),
            )
        } else if axiom_results
            .iter()
            .any(|r| r.status == EvaluationStatus::ConditionallyAcceptable)
        {
            (
                EvaluationStatus::ConditionallyAcceptable,
                true,
                false,
                None,
                "Mix of conditional and acceptable statements".to_string(),
            )
        } else {
            (
                EvaluationStatus::Acceptable,
                true,
                false,
                None,
                "All statements are normatively acceptable".to_string(),
            )
        };

        let num_acceptable = axiom_results
            .iter()
            .filter(|r| {
                r.status == EvaluationStatus::Acceptable
                    || r.status == EvaluationStatus::ConditionallyAcceptable
            })
            .count();

        ValidationResult {
            status,
            licensed,
            can_retry,
            feedback_hint,
            violated_axioms: violations,
            statement_results: statement_results.to_vec(),
            explanation,
            num_statements: statement_results.len(),
            num_acceptable,
            grounds_accepted: 0,
            grounds_cited: 0,
        }
    }

    fn to_judgment(&self, result: ValidationResult) -> AdmissibilityJudgment {
        let mut statement_evaluations = Vec::new();
        let mut violated_axioms = Vec::new();

        for stmt in &result.statement_results {
            let modality = stmt
                .statement
                .modality
                .clone()
                .map(|m| m.as_str().to_string())
                .unwrap_or_else(|| "unknown".to_string());
            let permitted = stmt
                .license
                .permitted_modalities
                .iter()
                .map(|m| m.as_str().to_string())
                .collect();

            let grounding_trace = stmt
                .ground_set
                .nodes
                .iter()
                .map(|k| GroundRef {
                    id: k.id.clone(),
                    scope: match k.scope {
                        crate::normative::Scope::Factual => "factual".to_string(),
                        crate::normative::Scope::Contextual => "contextual".to_string(),
                    },
                    source: match k.source {
                        crate::normative::Source::Observed => "observed".to_string(),
                        crate::normative::Source::Explicit => "explicit".to_string(),
                        crate::normative::Source::Inferred => "inferred".to_string(),
                        crate::normative::Source::Repeated => "repeated".to_string(),
                    },
                    status: match k.status {
                        crate::normative::Status::Hypothesis => "hypothesis".to_string(),
                        crate::normative::Status::Candidate => "candidate".to_string(),
                        crate::normative::Status::Confirmed => "confirmed".to_string(),
                    },
                    confidence: k.confidence,
                    strength: k.strength.clone(),
                    semantic_id: k.semantic_id.clone(),
                })
                .collect();

            statement_evaluations.push(StatementEvaluation {
                statement_id: stmt.statement.id.clone(),
                statement: stmt.statement.raw_text.clone(),
                modality,
                license: permitted,
                status: map_status(&stmt.status),
                violated_axiom: stmt.violated_axiom.clone(),
                explanation: stmt.explanation.clone(),
                grounding_trace,
                subject: Some(stmt.statement.subject.clone()),
                predicate: Some(stmt.statement.predicate.clone()),
            });
            if let Some(ax) = &stmt.violated_axiom {
                violated_axioms.push(ax.clone());
            }
        }

        AdmissibilityJudgment {
            status: map_status(&result.status),
            licensed: result.licensed,
            can_retry: result.can_retry,
            statement_evaluations,
            feedback_hint: result.feedback_hint,
            violated_axioms,
            explanation: result.explanation,
            num_statements: result.num_statements,
            num_acceptable: result.num_acceptable,
            grounds_accepted: result.grounds_accepted,
            grounds_cited: result.grounds_cited,
        }
    }

    fn extract_tool_results(
        &self,
        trajectory: &[ConversationMessage],
    ) -> Result<Vec<ToolResultSpeechAct>, EvaluateError> {
        let mut tool_results = Vec::new();

        let mut tool_call_by_id: BTreeMap<String, (String, BTreeMap<String, JsonValue>)> =
            BTreeMap::new();
        for message in trajectory {
            if message.role != "assistant" {
                continue;
            }
            for tool_call in &message.tool_calls {
                if tool_call.kind == "function" {
                    let args = parse_tool_args(tool_call.function_arguments.as_ref());
                    tool_call_by_id.insert(
                        tool_call.id.clone(),
                        (
                            tool_call
                                .function_name
                                .clone()
                                .unwrap_or_else(|| "unknown".to_string()),
                            args,
                        ),
                    );
                }
            }
        }

        for message in trajectory {
            if message.role == "tool" {
                let tool_call_id = message.tool_call_id.clone().unwrap_or_default();
                let (name, args) = tool_call_by_id
                    .get(&tool_call_id)
                    .cloned()
                    .unwrap_or_else(|| ("unknown".to_string(), BTreeMap::new()));
                let content = extract_text_content(message.content.as_ref())?;
                tool_results.push(ToolResultSpeechAct {
                    tool_name: name,
                    tool_call_id: Some(tool_call_id),
                    arguments: args,
                    result_text: content,
                });
            } else if message.role == "function"
                && let Some(name) = &message.function_name
            {
                let content = extract_text_content(message.content.as_ref())?;
                tool_results.push(ToolResultSpeechAct {
                    tool_name: name.clone(),
                    tool_call_id: None,
                    arguments: BTreeMap::new(),
                    result_text: content,
                });
            }
        }

        Ok(tool_results)
    }

    fn to_speech_act(
        &self,
        assistant_message: &ConversationMessage,
    ) -> Result<TextSpeechAct, EvaluateError> {
        let content = extract_text_content(assistant_message.content.as_ref())?;
        Ok(TextSpeechAct { text: content })
    }
}

fn map_status(status: &EvaluationStatus) -> AdmissibilityStatus {
    match status {
        EvaluationStatus::Acceptable => AdmissibilityStatus::Acceptable,
        EvaluationStatus::ConditionallyAcceptable => AdmissibilityStatus::ConditionallyAcceptable,
        EvaluationStatus::ViolatesNorm => AdmissibilityStatus::ViolatesNorm,
        EvaluationStatus::Unsupported => AdmissibilityStatus::Unsupported,
        EvaluationStatus::IllFormed => AdmissibilityStatus::IllFormed,
        EvaluationStatus::Underdetermined => AdmissibilityStatus::Underdetermined,
        EvaluationStatus::NoNormativeContent => AdmissibilityStatus::NoNormativeContent,
        EvaluationStatus::WellFormed => AdmissibilityStatus::Underdetermined,
    }
}

fn extract_text_content(content: Option<&JsonValue>) -> Result<String, EvaluateError> {
    let Some(content) = content else {
        return Ok(String::new());
    };
    match content {
        JsonValue::String(s) => Ok(s.clone()),
        JsonValue::Array(parts) => {
            let mut refusal_parts = Vec::new();
            let mut text_parts = Vec::new();
            for part in parts {
                let Some(obj) = part.as_object() else {
                    continue;
                };
                let kind = obj
                    .get("type")
                    .and_then(JsonValue::as_str)
                    .unwrap_or_default();
                if kind == "refusal"
                    && let Some(s) = obj.get("refusal").and_then(JsonValue::as_str)
                {
                    refusal_parts.push(s.to_string());
                }
                if kind == "text"
                    && let Some(s) = obj.get("text").and_then(JsonValue::as_str)
                {
                    text_parts.push(s.to_string());
                }
            }

            if !refusal_parts.is_empty() && !text_parts.is_empty() {
                return Err(EvaluateError::InvalidMessage(
                    "Assistant content cannot mix text and refusal parts".to_string(),
                ));
            }
            if !refusal_parts.is_empty() {
                Ok(refusal_parts.join("").trim().to_string())
            } else {
                Ok(text_parts.join("").trim().to_string())
            }
        }
        _ => Err(EvaluateError::LastAssistantContentNotString),
    }
}

fn parse_tool_args(arguments: Option<&JsonValue>) -> BTreeMap<String, JsonValue> {
    let Some(arguments) = arguments else {
        return BTreeMap::new();
    };

    match arguments {
        JsonValue::Object(map) => map.clone(),
        JsonValue::String(s) => match parse_json(s) {
            Ok(JsonValue::Object(map)) => map,
            _ => BTreeMap::new(),
        },
        _ => BTreeMap::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::json::parse_json;

    fn assistant_text(content: &str) -> ConversationMessage {
        ConversationMessage {
            role: "assistant".to_string(),
            content: Some(JsonValue::String(content.to_string())),
            tool_call_id: None,
            tool_calls: Vec::new(),
            function_name: None,
        }
    }

    #[test]
    fn evaluate_core_empty_agent_output() {
        let evaluator = AdmissibilityEvaluator::new();
        let result = evaluator.evaluate_core("", &[], None);
        assert_eq!(result.status, EvaluationStatus::Underdetermined);
        assert!(!result.licensed);
    }

    #[test]
    fn evaluate_core_no_normative_returns_no_normative_content() {
        let evaluator = AdmissibilityEvaluator::new();
        let result = evaluator.evaluate_core("hello", &[], None);
        assert_eq!(result.status, EvaluationStatus::NoNormativeContent);
    }

    #[test]
    fn parse_tool_args_variants() {
        assert_eq!(parse_tool_args(None).len(), 0);
        let parsed = parse_tool_args(Some(&parse_json(r#"{"a":1}"#).expect("json")));
        assert!(parsed.contains_key("a"));
        let parsed = parse_tool_args(Some(&JsonValue::String("{\"a\":1}".to_string())));
        assert!(parsed.contains_key("a"));
        let parsed = parse_tool_args(Some(&JsonValue::String("not json".to_string())));
        assert!(parsed.is_empty());
    }

    #[test]
    fn extract_tool_results_from_trajectory() {
        let evaluator = AdmissibilityEvaluator::new();
        let trajectory = vec![
            ConversationMessage {
                role: "assistant".to_string(),
                content: Some(JsonValue::String(String::new())),
                tool_call_id: None,
                tool_calls: vec![ToolCall {
                    id: "call1".to_string(),
                    kind: "function".to_string(),
                    function_name: Some("search".to_string()),
                    function_arguments: Some(JsonValue::String("{\"q\":\"x\"}".to_string())),
                    custom_name: None,
                    custom_input: None,
                }],
                function_name: None,
            },
            ConversationMessage {
                role: "tool".to_string(),
                content: Some(JsonValue::String("result".to_string())),
                tool_call_id: Some("call1".to_string()),
                tool_calls: Vec::new(),
                function_name: None,
            },
            ConversationMessage {
                role: "function".to_string(),
                content: Some(JsonValue::String("ok".to_string())),
                tool_call_id: None,
                tool_calls: Vec::new(),
                function_name: Some("legacy".to_string()),
            },
        ];

        let results = evaluator
            .extract_tool_results(&trajectory)
            .expect("must parse trajectory");
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].tool_name, "search");
        assert_eq!(results[1].tool_name, "legacy");
    }

    #[test]
    fn evaluate_with_conversation_and_citation() {
        let conversation = vec![
            ConversationMessage {
                role: "assistant".to_string(),
                content: Some(JsonValue::String(String::new())),
                tool_call_id: None,
                tool_calls: vec![ToolCall {
                    id: "callWeatherNYC".to_string(),
                    kind: "function".to_string(),
                    function_name: Some("get_weather".to_string()),
                    function_arguments: Some(JsonValue::String(
                        "{\"city\":\"New York\"}".to_string(),
                    )),
                    custom_name: None,
                    custom_input: None,
                }],
                function_name: None,
            },
            ConversationMessage {
                role: "tool".to_string(),
                content: Some(JsonValue::String(
                    "{\"weather_id\":\"nyc_2026-02-07\"}".to_string(),
                )),
                tool_call_id: Some("callWeatherNYC".to_string()),
                tool_calls: Vec::new(),
                function_name: None,
            },
            assistant_text("You should carry an umbrella [@callWeatherNYC]."),
        ];

        let result = evaluate(EvaluateInput {
            agent_output: None,
            conversation: Some(conversation),
            grounds: None,
        })
        .expect("evaluation must succeed");

        assert_eq!(result.status, AdmissibilityStatus::Acceptable);
        assert!(result.grounds_accepted >= 1);
        assert!(result.grounds_cited >= 1);
    }

    #[test]
    fn evaluate_mismatched_agent_output_fails() {
        let conversation = vec![assistant_text("Use umbrella [@callWeatherNYC].")];
        let err = evaluate(EvaluateInput {
            agent_output: Some("Different output".to_string()),
            conversation: Some(conversation),
            grounds: None,
        })
        .unwrap_err();
        assert_eq!(err, EvaluateError::AgentOutputMismatch);
    }

    #[test]
    fn parse_conversation_from_json_array() {
        let input = parse_json(r#"[{"role":"assistant","content":"hi","tool_calls":[]}]"#)
            .expect("json parses");
        let JsonValue::Array(arr) = input else {
            panic!("array expected")
        };
        let messages = parse_conversation(&arr).expect("conversation parses");
        assert_eq!(messages.len(), 1);
        assert_eq!(messages[0].role, "assistant");
    }
}
