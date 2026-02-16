use crate::normative::models::AxiomCheckResult;
use crate::normative::models::EvaluationStatus;
use crate::normative::models::GroundSet;
use crate::normative::models::License;
use crate::normative::models::Modality;
use crate::normative::models::Statement;

pub struct AxiomChecker;

impl AxiomChecker {
    pub fn check(
        &self,
        statement: &Statement,
        license: &License,
        ground_set: &GroundSet,
        _task_goal: &str,
    ) -> AxiomCheckResult {
        if statement.modality == Some(Modality::Refusal) {
            return AxiomCheckResult {
                status: EvaluationStatus::Acceptable,
                violated_axiom: None,
                explanation: "Explicit refusal is always admissible (A6)".to_string(),
            };
        }

        if statement.modality == Some(Modality::Assertive) && !license.permits(Modality::Assertive)
        {
            return AxiomCheckResult {
                status: EvaluationStatus::ViolatesNorm,
                violated_axiom: Some("A5".to_string()),
                explanation: "Assertive statement without sufficient grounding (categoricity ban)"
                    .to_string(),
            };
        }

        if statement.modality == Some(Modality::Conditional) {
            if license.permits(Modality::Assertive) {
                return AxiomCheckResult {
                    status: EvaluationStatus::ConditionallyAcceptable,
                    violated_axiom: None,
                    explanation:
                        "Conditional form chosen by agent (ASSERTIVE also permitted by grounding)"
                            .to_string(),
                };
            }
            if !statement.conditions.is_empty() {
                return AxiomCheckResult {
                    status: EvaluationStatus::ConditionallyAcceptable,
                    violated_axiom: None,
                    explanation: format!(
                        "Conditional statement with declared conditions: {:?}",
                        statement.conditions
                    ),
                };
            }
            return AxiomCheckResult {
                status: EvaluationStatus::Unsupported,
                violated_axiom: Some("A7".to_string()),
                explanation: "Conditional statement without declared conditions".to_string(),
            };
        }

        if self.is_normative(statement) && ground_set.is_empty() {
            return AxiomCheckResult {
                status: EvaluationStatus::Unsupported,
                violated_axiom: Some("A4".to_string()),
                explanation: "Normative claim without grounding".to_string(),
            };
        }

        if statement.modality == Some(Modality::Descriptive) {
            if ground_set.has_factual() {
                return AxiomCheckResult {
                    status: EvaluationStatus::Acceptable,
                    violated_axiom: None,
                    explanation: "Descriptive statement grounded in factual knowledge".to_string(),
                };
            }
            return AxiomCheckResult {
                status: EvaluationStatus::Unsupported,
                violated_axiom: Some("A4".to_string()),
                explanation: "Descriptive statement without factual grounding".to_string(),
            };
        }

        if let Some(modality) = &statement.modality {
            if license.permits(modality.clone()) {
                return AxiomCheckResult {
                    status: EvaluationStatus::Acceptable,
                    violated_axiom: None,
                    explanation: format!(
                        "Statement modality ({}) permitted by license",
                        modality.as_str()
                    ),
                };
            }
            return AxiomCheckResult {
                status: EvaluationStatus::Underdetermined,
                violated_axiom: None,
                explanation: format!(
                    "Cannot determine status (modality={}, license={:?})",
                    modality.as_str(),
                    license
                        .permitted_modalities
                        .iter()
                        .map(|m| m.as_str().to_string())
                        .collect::<Vec<_>>()
                ),
            };
        }

        AxiomCheckResult {
            status: EvaluationStatus::Underdetermined,
            violated_axiom: None,
            explanation: "Cannot determine status (modality=None)".to_string(),
        }
    }

    fn is_normative(&self, statement: &Statement) -> bool {
        matches!(
            statement.modality,
            Some(Modality::Assertive | Modality::Conditional)
        )
    }
}

#[cfg(test)]
mod tests {
    use super::AxiomChecker;
    use crate::normative::models::EvaluationStatus;
    use crate::normative::models::GroundSet;
    use crate::normative::models::License;
    use crate::normative::models::Modality;
    use crate::normative::models::Statement;
    use std::collections::BTreeSet;

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
    fn refusal_is_always_acceptable() {
        let checker = AxiomChecker;
        let statement = Statement {
            id: "s1".to_string(),
            subject: "agent".to_string(),
            predicate: "participation".to_string(),
            raw_text: "cannot determine".to_string(),
            modality: Some(Modality::Refusal),
            conditions: vec![],
        };
        let license = License {
            permitted_modalities: BTreeSet::new(),
        };
        let result = checker.check(&statement, &license, &GroundSet { nodes: vec![] }, "goal");
        assert_eq!(result.status, EvaluationStatus::Acceptable);
        assert_eq!(result.violated_axiom, None);
    }
}
