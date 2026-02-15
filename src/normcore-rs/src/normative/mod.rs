mod axiom_checker;
mod extractor;
mod ground_matcher;
mod knowledge_builder;
mod license_deriver;
mod modality_detector;
mod models;

pub use axiom_checker::AxiomChecker;
pub use extractor::StatementExtractor;
pub use ground_matcher::GroundSetMatcher;
pub use knowledge_builder::KnowledgeStateBuilder;
pub use license_deriver::LicenseDeriver;
pub use modality_detector::ModalityDetector;
pub use models::AxiomCheckResult;
pub use models::EvaluationStatus;
pub use models::GroundSet;
pub use models::KnowledgeNode;
pub use models::License;
pub use models::Modality;
pub use models::Scope;
pub use models::Source;
pub use models::Statement;
pub use models::StatementValidationResult;
pub use models::Status;
pub use models::ValidationResult;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::CreatorType;
    use crate::models::EvidenceType;
    use crate::models::Ground;
    use crate::models::LinkRole;
    use crate::models::LinkSet;
    use crate::models::Provenance;
    use crate::models::StatementGroundLink;
    use crate::models::ToolResultSpeechAct;
    use std::collections::BTreeMap;
    use std::collections::BTreeSet;

    fn node(id: &str, scope: Scope, strength: &str) -> KnowledgeNode {
        KnowledgeNode::new(
            id.to_string(),
            Source::Observed,
            Status::Confirmed,
            1.0,
            scope,
            strength.to_string(),
            Some(format!("sem_{id}")),
        )
        .expect("must create node")
    }

    #[test]
    fn extractor_protocol_only_returns_empty() {
        let ex = StatementExtractor;
        assert!(ex.extract("Hello! How can I help you today?").is_empty());
    }

    #[test]
    fn detector_goal_conditional_over_recommendation() {
        let d = ModalityDetector;
        assert_eq!(
            d.detect("If your goal is speed, X is better."),
            Modality::Conditional
        );
    }

    #[test]
    fn axiom_assertive_without_license_violates_a5() {
        let checker = AxiomChecker;
        let statement = Statement {
            id: "s1".to_string(),
            subject: "agent".to_string(),
            predicate: "participation".to_string(),
            raw_text: "text".to_string(),
            modality: Some(Modality::Assertive),
            conditions: vec![],
        };
        let mut permitted = BTreeSet::new();
        permitted.insert(Modality::Refusal);
        let license = License {
            permitted_modalities: permitted,
        };
        let result = checker.check(&statement, &license, &GroundSet { nodes: vec![] }, "goal");
        assert_eq!(result.status, EvaluationStatus::ViolatesNorm);
        assert_eq!(result.violated_axiom, Some("A5".to_string()));
    }

    #[test]
    fn license_with_links_strong_supports_assertive() {
        let deriver = LicenseDeriver;
        let ground_set = GroundSet {
            nodes: vec![node("n1", Scope::Factual, "strong")],
        };
        let link = StatementGroundLink {
            statement_id: "s1".to_string(),
            ground_id: "n1".to_string(),
            role: LinkRole::Supports,
            provenance: Provenance {
                creator: CreatorType::Human,
                evidence_type: EvidenceType::Explicit,
                evidence_content: None,
                signature: None,
            },
        };
        let license = deriver.derive(&ground_set, Some(&LinkSet { links: vec![link] }));
        assert!(license.permits(Modality::Assertive));
    }

    #[test]
    fn knowledge_builder_extracts_semantic_id() {
        let builder = KnowledgeStateBuilder;
        let result = ToolResultSpeechAct {
            tool_name: "get_issue".to_string(),
            tool_call_id: None,
            arguments: BTreeMap::new(),
            result_text: "{\"issue_id\":\"123\"}".to_string(),
        };
        let node = builder
            .tool_result_to_knowledge(&result)
            .expect("must produce node");
        assert_eq!(node[0].semantic_id, Some("issue_123".to_string()));
    }

    #[test]
    fn materialize_external_grounds_injects_missing() {
        let builder = KnowledgeStateBuilder;
        let initial = vec![node("tool_weather", Scope::Factual, "strong")];
        let grounds = vec![Ground {
            citation_key: "file_hist".to_string(),
            ground_id: "archive_nyc_weather_2025-02-07".to_string(),
            role: LinkRole::Supports,
            creator: CreatorType::UpstreamPipeline,
            evidence_type: EvidenceType::Observation,
            evidence_content: None,
            signature: None,
        }];

        let out = builder.materialize_external_grounds(&initial, &grounds);
        assert!(
            out.iter()
                .any(|node| node.id == "archive_nyc_weather_2025-02-07")
        );
    }
}
