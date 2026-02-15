use crate::json::JsonValue;
use std::collections::BTreeMap;
use std::collections::BTreeSet;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AdmissibilityStatus {
    Acceptable,
    ConditionallyAcceptable,
    ViolatesNorm,
    Unsupported,
    IllFormed,
    Underdetermined,
    NoNormativeContent,
}

impl AdmissibilityStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            AdmissibilityStatus::Acceptable => "acceptable",
            AdmissibilityStatus::ConditionallyAcceptable => "conditionally_acceptable",
            AdmissibilityStatus::ViolatesNorm => "violates_norm",
            AdmissibilityStatus::Unsupported => "unsupported",
            AdmissibilityStatus::IllFormed => "ill_formed",
            AdmissibilityStatus::Underdetermined => "underdetermined",
            AdmissibilityStatus::NoNormativeContent => "no_normative_content",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct GroundRef {
    pub id: String,
    pub scope: String,
    pub source: String,
    pub status: String,
    pub confidence: f64,
    pub strength: String,
    pub semantic_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StatementEvaluation {
    pub statement_id: String,
    pub statement: String,
    pub modality: String,
    pub license: BTreeSet<String>,
    pub status: AdmissibilityStatus,
    pub violated_axiom: Option<String>,
    pub explanation: String,
    pub grounding_trace: Vec<GroundRef>,
    pub subject: Option<String>,
    pub predicate: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AdmissibilityJudgment {
    pub status: AdmissibilityStatus,
    pub licensed: bool,
    pub can_retry: bool,
    pub statement_evaluations: Vec<StatementEvaluation>,
    pub feedback_hint: Option<String>,
    pub violated_axioms: Vec<String>,
    pub explanation: String,
    pub num_statements: usize,
    pub num_acceptable: usize,
    pub grounds_accepted: usize,
    pub grounds_cited: usize,
}

impl AdmissibilityJudgment {
    pub fn to_json_value(&self) -> JsonValue {
        let mut obj = BTreeMap::new();
        obj.insert(
            "status".to_string(),
            JsonValue::String(self.status.as_str().to_string()),
        );
        obj.insert("licensed".to_string(), JsonValue::Bool(self.licensed));
        obj.insert("can_retry".to_string(), JsonValue::Bool(self.can_retry));
        obj.insert(
            "statement_evaluations".to_string(),
            JsonValue::Array(
                self.statement_evaluations
                    .iter()
                    .map(statement_eval_to_json)
                    .collect(),
            ),
        );
        if let Some(feedback) = &self.feedback_hint {
            obj.insert(
                "feedback_hint".to_string(),
                JsonValue::String(feedback.clone()),
            );
        } else {
            obj.insert("feedback_hint".to_string(), JsonValue::Null);
        }
        obj.insert(
            "violated_axioms".to_string(),
            JsonValue::Array(
                self.violated_axioms
                    .iter()
                    .map(|v| JsonValue::String(v.clone()))
                    .collect(),
            ),
        );
        obj.insert(
            "explanation".to_string(),
            JsonValue::String(self.explanation.clone()),
        );
        obj.insert(
            "num_statements".to_string(),
            JsonValue::Number(self.num_statements as f64),
        );
        obj.insert(
            "num_acceptable".to_string(),
            JsonValue::Number(self.num_acceptable as f64),
        );
        obj.insert(
            "grounds_accepted".to_string(),
            JsonValue::Number(self.grounds_accepted as f64),
        );
        obj.insert(
            "grounds_cited".to_string(),
            JsonValue::Number(self.grounds_cited as f64),
        );
        JsonValue::Object(obj)
    }
}

fn statement_eval_to_json(value: &StatementEvaluation) -> JsonValue {
    let mut obj = BTreeMap::new();
    obj.insert(
        "statement_id".to_string(),
        JsonValue::String(value.statement_id.clone()),
    );
    obj.insert(
        "statement".to_string(),
        JsonValue::String(value.statement.clone()),
    );
    obj.insert(
        "modality".to_string(),
        JsonValue::String(value.modality.clone()),
    );
    obj.insert(
        "license".to_string(),
        JsonValue::Array(
            value
                .license
                .iter()
                .map(|m| JsonValue::String(m.clone()))
                .collect(),
        ),
    );
    obj.insert(
        "status".to_string(),
        JsonValue::String(value.status.as_str().to_string()),
    );
    if let Some(ax) = &value.violated_axiom {
        obj.insert("violated_axiom".to_string(), JsonValue::String(ax.clone()));
    } else {
        obj.insert("violated_axiom".to_string(), JsonValue::Null);
    }
    obj.insert(
        "explanation".to_string(),
        JsonValue::String(value.explanation.clone()),
    );
    obj.insert(
        "grounding_trace".to_string(),
        JsonValue::Array(
            value
                .grounding_trace
                .iter()
                .map(ground_ref_to_json)
                .collect(),
        ),
    );
    match &value.subject {
        Some(s) => obj.insert("subject".to_string(), JsonValue::String(s.clone())),
        None => obj.insert("subject".to_string(), JsonValue::Null),
    };
    match &value.predicate {
        Some(s) => obj.insert("predicate".to_string(), JsonValue::String(s.clone())),
        None => obj.insert("predicate".to_string(), JsonValue::Null),
    };
    JsonValue::Object(obj)
}

fn ground_ref_to_json(value: &GroundRef) -> JsonValue {
    let mut obj = BTreeMap::new();
    obj.insert("id".to_string(), JsonValue::String(value.id.clone()));
    obj.insert("scope".to_string(), JsonValue::String(value.scope.clone()));
    obj.insert(
        "source".to_string(),
        JsonValue::String(value.source.clone()),
    );
    obj.insert(
        "status".to_string(),
        JsonValue::String(value.status.clone()),
    );
    obj.insert(
        "confidence".to_string(),
        JsonValue::Number(value.confidence),
    );
    obj.insert(
        "strength".to_string(),
        JsonValue::String(value.strength.clone()),
    );
    if let Some(sid) = &value.semantic_id {
        obj.insert("semantic_id".to_string(), JsonValue::String(sid.clone()));
    } else {
        obj.insert("semantic_id".to_string(), JsonValue::Null);
    }
    JsonValue::Object(obj)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContentPart {
    Text(String),
    Refusal(String),
}

#[derive(Debug, Clone, PartialEq)]
pub struct ToolCall {
    pub id: String,
    pub kind: String,
    pub function_name: Option<String>,
    pub function_arguments: Option<JsonValue>,
    pub custom_name: Option<String>,
    pub custom_input: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ConversationMessage {
    pub role: String,
    pub content: Option<JsonValue>,
    pub tool_call_id: Option<String>,
    pub tool_calls: Vec<ToolCall>,
    pub function_name: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LinkRole {
    Supports,
    Disambiguates,
    Contextualizes,
}

impl LinkRole {
    pub fn as_str(&self) -> &'static str {
        match self {
            LinkRole::Supports => "supports",
            LinkRole::Disambiguates => "disambiguates",
            LinkRole::Contextualizes => "contextualizes",
        }
    }
}

impl std::str::FromStr for LinkRole {
    type Err = ();

    fn from_str(v: &str) -> Result<Self, Self::Err> {
        match v {
            "supports" => Ok(LinkRole::Supports),
            "disambiguates" => Ok(LinkRole::Disambiguates),
            "contextualizes" => Ok(LinkRole::Contextualizes),
            _ => Err(()),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreatorType {
    Human,
    ToolObserver,
    AgentDeclaration,
    UpstreamPipeline,
}

impl CreatorType {
    pub fn as_str(&self) -> &'static str {
        match self {
            CreatorType::Human => "human",
            CreatorType::ToolObserver => "tool_observer",
            CreatorType::AgentDeclaration => "agent_declaration",
            CreatorType::UpstreamPipeline => "upstream_pipeline",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvidenceType {
    Observation,
    Explicit,
    Structural,
    Validation,
}

impl EvidenceType {
    pub fn as_str(&self) -> &'static str {
        match self {
            EvidenceType::Observation => "observation",
            EvidenceType::Explicit => "explicit",
            EvidenceType::Structural => "structural",
            EvidenceType::Validation => "validation",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Provenance {
    pub creator: CreatorType,
    pub evidence_type: EvidenceType,
    pub evidence_content: Option<String>,
    pub signature: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StatementGroundLink {
    pub statement_id: String,
    pub ground_id: String,
    pub role: LinkRole,
    pub provenance: Provenance,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkSet {
    pub links: Vec<StatementGroundLink>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Ground {
    pub citation_key: String,
    pub ground_id: String,
    pub role: LinkRole,
    pub creator: CreatorType,
    pub evidence_type: EvidenceType,
    pub evidence_content: Option<String>,
    pub signature: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ToolResultSpeechAct {
    pub tool_name: String,
    pub tool_call_id: Option<String>,
    pub arguments: BTreeMap<String, JsonValue>,
    pub result_text: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TextSpeechAct {
    pub text: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RefusalSpeechAct {
    pub refusal: String,
}
