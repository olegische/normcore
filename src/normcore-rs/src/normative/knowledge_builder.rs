use crate::json::JsonValue;
use crate::json::parse_json;
use crate::models::Ground;
use crate::models::ToolResultSpeechAct;
use crate::normative::models::KnowledgeNode;
use crate::normative::models::Scope;
use crate::normative::models::Source;
use crate::normative::models::Status;
use std::collections::BTreeMap;
use std::collections::HashSet;

pub struct KnowledgeStateBuilder;

impl KnowledgeStateBuilder {
    pub fn build(&self, tool_results: &[ToolResultSpeechAct]) -> Vec<KnowledgeNode> {
        let (nodes, _) = self.build_with_references(tool_results);
        nodes
    }

    pub fn build_with_references(
        &self,
        tool_results: &[ToolResultSpeechAct],
    ) -> (Vec<KnowledgeNode>, BTreeMap<String, Vec<String>>) {
        let mut nodes = Vec::new();
        let mut refs: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for result in tool_results {
            let maybe = self.tool_result_to_knowledge(result);
            let produced = match maybe {
                None => continue,
                Some(v) => v,
            };
            let ids: Vec<String> = produced
                .iter()
                .map(|n| n.semantic_id.clone().unwrap_or_else(|| n.id.clone()))
                .collect();
            if let Some(call_id) = &result.tool_call_id
                && !ids.is_empty()
            {
                refs.insert(call_id.clone(), ids);
            }
            nodes.extend(produced);
        }
        (nodes, refs)
    }

    pub fn materialize_external_grounds(
        &self,
        knowledge_nodes: &[KnowledgeNode],
        grounds: &[Ground],
    ) -> Vec<KnowledgeNode> {
        if grounds.is_empty() {
            return knowledge_nodes.to_vec();
        }
        let existing_ids: HashSet<String> = knowledge_nodes.iter().map(|n| n.id.clone()).collect();
        let existing_semantic_ids: HashSet<String> = knowledge_nodes
            .iter()
            .filter_map(|n| n.semantic_id.clone())
            .collect();

        let mut expanded = knowledge_nodes.to_vec();
        for ground in grounds {
            if existing_ids.contains(&ground.ground_id)
                || existing_semantic_ids.contains(&ground.ground_id)
            {
                continue;
            }
            let node = KnowledgeNode::new(
                ground.ground_id.clone(),
                Source::Observed,
                Status::Confirmed,
                1.0,
                Scope::Factual,
                "strong".to_string(),
                Some(ground.ground_id.clone()),
            )
            .expect("known-valid node");
            expanded.push(node);
        }
        expanded
    }

    pub fn tool_result_to_knowledge(
        &self,
        tool_result: &ToolResultSpeechAct,
    ) -> Option<Vec<KnowledgeNode>> {
        let tool_name = if tool_result.tool_name.is_empty() {
            "unknown"
        } else {
            &tool_result.tool_name
        };
        if self.is_non_epistemic_tool(tool_name) {
            return None;
        }

        let extracted = self.extract_semantic_id(tool_result);
        if let Some(SemanticExtract::Many(ids)) = extracted.clone() {
            let mut out = Vec::new();
            for (idx, sid) in ids.into_iter().enumerate() {
                let stable = stable_id_fragment(&format!("{tool_name}:{sid}"));
                out.push(
                    KnowledgeNode::new(
                        format!("tool_{tool_name}_item{idx}_{stable}"),
                        Source::Observed,
                        Status::Confirmed,
                        1.0,
                        Scope::Factual,
                        "strong".to_string(),
                        Some(sid),
                    )
                    .expect("known-valid node"),
                );
            }
            return Some(out);
        }

        let semantic_id = match extracted {
            Some(SemanticExtract::One(v)) => Some(v),
            _ => None,
        };
        let stable = stable_id_fragment(&format!(
            "{}:{}:{}",
            tool_name,
            tool_result.result_text,
            tool_result.tool_call_id.clone().unwrap_or_default()
        ));
        Some(vec![
            KnowledgeNode::new(
                format!("tool_{tool_name}_{stable}"),
                Source::Observed,
                Status::Confirmed,
                1.0,
                Scope::Factual,
                "strong".to_string(),
                semantic_id,
            )
            .expect("known-valid node"),
        ])
    }

    fn is_non_epistemic_tool(&self, tool_name: &str) -> bool {
        let name = tool_name.to_lowercase();
        if name == "get_user_cognitive_context" {
            return true;
        }
        if name.contains("personalization") || name.contains("personal_context") {
            return true;
        }
        if name.contains("memory")
            && [
                "save",
                "note",
                "notes",
                "load",
                "consolidat",
                "distill",
                "state",
            ]
            .iter()
            .any(|k| name.contains(k))
        {
            return true;
        }
        if name.contains("profile")
            && ["save", "set", "update", "load", "consolidat"]
                .iter()
                .any(|k| name.contains(k))
        {
            return true;
        }
        [
            "remember",
            "preference",
            "preferences",
            "setting",
            "settings",
        ]
        .iter()
        .any(|k| name.contains(k))
    }

    fn extract_semantic_id(&self, tool_result: &ToolResultSpeechAct) -> Option<SemanticExtract> {
        if tool_result.result_text.trim().is_empty() {
            return None;
        }
        let Ok(data) = parse_json(&tool_result.result_text) else {
            return None;
        };

        match data {
            JsonValue::Array(items) => {
                let mut ids = Vec::new();
                for item in items {
                    if let JsonValue::Object(map) = item
                        && let Some(id) = extract_entity_id(&map)
                    {
                        ids.push(id);
                    }
                }
                if ids.is_empty() {
                    None
                } else {
                    Some(SemanticExtract::Many(ids))
                }
            }
            JsonValue::Object(map) => extract_entity_id(&map).map(SemanticExtract::One),
            _ => None,
        }
    }
}

#[derive(Clone)]
enum SemanticExtract {
    One(String),
    Many(Vec<String>),
}

fn extract_entity_id(map: &BTreeMap<String, JsonValue>) -> Option<String> {
    for (field, value) in map {
        if let Some(prefix) = field.strip_suffix("_key")
            && let Some(v) = value.as_str()
        {
            return Some(format!("{prefix}_{v}"));
        }
    }
    for (field, value) in map {
        if let Some(prefix) = field.strip_suffix("_id")
            && let Some(v) = value.as_str()
        {
            return Some(format!("{prefix}_{v}"));
        }
    }
    None
}

fn stable_id_fragment(value: &str) -> String {
    let mut hash: u64 = 1469598103934665603;
    for b in value.as_bytes() {
        hash ^= *b as u64;
        hash = hash.wrapping_mul(1099511628211);
    }
    let hex = format!("{hash:016x}");
    hex[..10].to_string()
}
