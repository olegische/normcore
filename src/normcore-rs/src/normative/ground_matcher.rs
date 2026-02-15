use crate::normative::models::GroundSet;
use crate::normative::models::KnowledgeNode;
use crate::normative::models::Modality;
use crate::normative::models::Scope;
use crate::normative::models::Statement;

pub struct GroundSetMatcher;

impl GroundSetMatcher {
    pub fn match_nodes(
        &self,
        statement: &Statement,
        knowledge_nodes: &[KnowledgeNode],
    ) -> GroundSet {
        let mut relevant = Vec::new();
        for k in knowledge_nodes {
            if self.is_relevant(statement, k) {
                relevant.push(k.clone());
            }
        }
        GroundSet { nodes: relevant }
    }

    fn is_relevant(&self, statement: &Statement, node: &KnowledgeNode) -> bool {
        match statement.modality {
            Some(Modality::Descriptive) => node.scope == Scope::Factual,
            Some(Modality::Assertive) | Some(Modality::Conditional) => {
                node.scope == Scope::Factual || node.scope == Scope::Contextual
            }
            Some(Modality::Refusal) => false,
            None => false,
        }
    }
}
