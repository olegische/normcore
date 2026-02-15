use std::collections::BTreeSet;

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Modality {
    Assertive,
    Conditional,
    Refusal,
    Descriptive,
}

impl Modality {
    pub fn as_str(&self) -> &'static str {
        match self {
            Modality::Assertive => "assertive",
            Modality::Conditional => "conditional",
            Modality::Refusal => "refusal",
            Modality::Descriptive => "descriptive",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Source {
    Observed,
    Explicit,
    Inferred,
    Repeated,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Status {
    Hypothesis,
    Candidate,
    Confirmed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Scope {
    Factual,
    Contextual,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EvaluationStatus {
    WellFormed,
    IllFormed,
    Unsupported,
    Underdetermined,
    ConditionallyAcceptable,
    ViolatesNorm,
    Acceptable,
    NoNormativeContent,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Statement {
    pub id: String,
    pub subject: String,
    pub predicate: String,
    pub raw_text: String,
    pub modality: Option<Modality>,
    pub conditions: Vec<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct KnowledgeNode {
    pub id: String,
    pub source: Source,
    pub status: Status,
    pub confidence: f64,
    pub scope: Scope,
    pub strength: String,
    pub semantic_id: Option<String>,
}

impl KnowledgeNode {
    pub fn new(
        id: String,
        source: Source,
        status: Status,
        confidence: f64,
        scope: Scope,
        strength: String,
        semantic_id: Option<String>,
    ) -> Result<Self, String> {
        if !(0.0..=1.0).contains(&confidence) {
            return Err(format!(
                "Confidence must be in [0.0, 1.0], got {confidence}"
            ));
        }
        if strength != "strong" && strength != "weak" {
            return Err(format!(
                "Strength must be 'strong' or 'weak', got {strength}"
            ));
        }
        Ok(Self {
            id,
            source,
            status,
            confidence,
            scope,
            strength,
            semantic_id,
        })
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct GroundSet {
    pub nodes: Vec<KnowledgeNode>,
}

impl GroundSet {
    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    pub fn has_factual(&self) -> bool {
        self.nodes.iter().any(|k| k.scope == Scope::Factual)
    }

    pub fn has_scope(&self, scope: Scope) -> bool {
        self.nodes.iter().any(|k| k.scope == scope)
    }

    pub fn get_scope_strength(&self, scope: Scope) -> Option<String> {
        let mut found_any = false;
        for n in &self.nodes {
            if n.scope == scope {
                found_any = true;
                if n.strength == "strong" {
                    return Some("strong".to_string());
                }
            }
        }
        if found_any {
            Some("weak".to_string())
        } else {
            None
        }
    }

    pub fn has_strong_in_scope(&self, scope: Scope) -> bool {
        self.nodes
            .iter()
            .any(|k| k.scope == scope && k.strength == "strong")
    }

    pub fn resolve_ground(&self, ground_id: &str) -> Option<KnowledgeNode> {
        for n in &self.nodes {
            if n.id == ground_id {
                return Some(n.clone());
            }
        }
        for n in &self.nodes {
            if n.semantic_id.as_deref() == Some(ground_id) {
                return Some(n.clone());
            }
        }
        None
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct License {
    pub permitted_modalities: BTreeSet<Modality>,
}

impl License {
    pub fn permits(&self, modality: Modality) -> bool {
        self.permitted_modalities.contains(&modality)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AxiomCheckResult {
    pub status: EvaluationStatus,
    pub violated_axiom: Option<String>,
    pub explanation: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StatementValidationResult {
    pub statement: Statement,
    pub status: EvaluationStatus,
    pub license: License,
    pub ground_set: GroundSet,
    pub violated_axiom: Option<String>,
    pub explanation: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ValidationResult {
    pub status: EvaluationStatus,
    pub licensed: bool,
    pub can_retry: bool,
    pub feedback_hint: Option<String>,
    pub violated_axioms: Vec<String>,
    pub statement_results: Vec<StatementValidationResult>,
    pub explanation: String,
    pub num_statements: usize,
    pub num_acceptable: usize,
    pub grounds_accepted: usize,
    pub grounds_cited: usize,
}
