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

#[cfg(test)]
mod tests {
    use super::GroundSetMatcher;
    use crate::normative::models::KnowledgeNode;
    use crate::normative::models::Modality;
    use crate::normative::models::Scope;
    use crate::normative::models::Source;
    use crate::normative::models::Statement;
    use crate::normative::models::Status;

    fn node(id: &str, scope: Scope) -> KnowledgeNode {
        KnowledgeNode::new(
            id.to_string(),
            Source::Observed,
            Status::Confirmed,
            1.0,
            scope,
            "strong".to_string(),
            None,
        )
        .expect("must create node")
    }

    fn statement(modality: Modality) -> Statement {
        Statement {
            id: "s1".to_string(),
            subject: "agent".to_string(),
            predicate: "participation".to_string(),
            raw_text: "text".to_string(),
            modality: Some(modality),
            conditions: vec![],
        }
    }

    #[test]
    fn descriptive_keeps_only_factual_nodes() {
        let matcher = GroundSetMatcher;
        let stmt = statement(Modality::Descriptive);
        let grounds = matcher.match_nodes(
            &stmt,
            &[node("f", Scope::Factual), node("c", Scope::Contextual)],
        );
        assert_eq!(grounds.nodes.len(), 1);
        assert_eq!(grounds.nodes[0].id, "f");
    }

    #[test]
    fn assertive_keeps_factual_and_contextual_nodes() {
        let matcher = GroundSetMatcher;
        let stmt = statement(Modality::Assertive);
        let grounds = matcher.match_nodes(
            &stmt,
            &[node("f", Scope::Factual), node("c", Scope::Contextual)],
        );
        assert_eq!(grounds.nodes.len(), 2);
    }
}
