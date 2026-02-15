use crate::json::JsonValue;
use crate::models::CreatorType;
use crate::models::EvidenceType;
use crate::models::Ground;
use crate::models::LinkRole;
use crate::models::LinkSet;
use crate::models::Provenance;
use crate::models::StatementGroundLink;
use std::collections::BTreeMap;
use std::collections::HashSet;

pub fn parse_grounds(payload: &[JsonValue]) -> Vec<Ground> {
    let mut grounds = Vec::new();
    for item in payload {
        let Some(obj) = item.as_object() else {
            continue;
        };
        let Some(citation_key) = obj.get("citation_key").and_then(JsonValue::as_str) else {
            continue;
        };
        let Some(ground_id) = obj.get("ground_id").and_then(JsonValue::as_str) else {
            continue;
        };
        grounds.push(Ground {
            citation_key: citation_key.to_string(),
            ground_id: ground_id.to_string(),
            role: LinkRole::Supports,
            creator: CreatorType::UpstreamPipeline,
            evidence_type: EvidenceType::Observation,
            evidence_content: obj
                .get("evidence_content")
                .and_then(JsonValue::as_str)
                .map(ToString::to_string),
            signature: obj
                .get("signature")
                .and_then(JsonValue::as_str)
                .map(ToString::to_string),
        });
    }
    grounds
}

pub fn extract_citation_keys(text: &str) -> Vec<String> {
    if text.is_empty() {
        return Vec::new();
    }
    let bytes = text.as_bytes();
    let mut i = 0;
    let mut keys = Vec::new();
    let mut seen = HashSet::new();

    while i + 2 < bytes.len() {
        if bytes[i] == b'[' && bytes[i + 1] == b'@' {
            let start = i + 2;
            let mut end = start;
            while end < bytes.len() && bytes[end] != b']' {
                end += 1;
            }
            if end < bytes.len() && end > start {
                let candidate = &text[start..end];
                if is_valid_citation_key(candidate) && !seen.contains(candidate) {
                    seen.insert(candidate.to_string());
                    keys.push(candidate.to_string());
                }
            }
            i = end;
        }
        i += 1;
    }

    keys
}

fn is_valid_citation_key(key: &str) -> bool {
    let mut chars = key.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if !first.is_ascii_alphabetic() {
        return false;
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
}

pub fn build_links_from_grounds(text: &str, grounds: &[Ground], statement_id: &str) -> LinkSet {
    let mut by_key: BTreeMap<String, Vec<&Ground>> = BTreeMap::new();
    for ground in grounds {
        by_key
            .entry(ground.citation_key.clone())
            .or_default()
            .push(ground);
    }

    let mut links = Vec::new();
    for key in extract_citation_keys(text) {
        if let Some(list) = by_key.get(&key) {
            for ground in list {
                links.push(StatementGroundLink {
                    statement_id: statement_id.to_string(),
                    ground_id: ground.ground_id.clone(),
                    role: ground.role.clone(),
                    provenance: Provenance {
                        creator: ground.creator.clone(),
                        evidence_type: ground.evidence_type.clone(),
                        evidence_content: Some(
                            ground
                                .evidence_content
                                .clone()
                                .unwrap_or_else(|| format!("citation_key={key}")),
                        ),
                        signature: ground.signature.clone(),
                    },
                });
            }
        }
    }

    LinkSet { links }
}

pub fn grounds_from_tool_call_refs(
    tool_call_refs: &std::collections::BTreeMap<String, Vec<String>>,
) -> Vec<Ground> {
    let mut out = Vec::new();
    for (citation_key, ground_ids) in tool_call_refs {
        for ground_id in ground_ids {
            out.push(Ground {
                citation_key: citation_key.clone(),
                ground_id: ground_id.clone(),
                role: LinkRole::Supports,
                creator: CreatorType::ToolObserver,
                evidence_type: EvidenceType::Observation,
                evidence_content: Some(format!("tool_call_id={citation_key}")),
                signature: None,
            });
        }
    }
    out
}

pub fn parse_openai_citations(citations: &[JsonValue]) -> Vec<JsonValue> {
    let mut out = Vec::new();
    for item in citations {
        let Some(obj) = item.as_object() else {
            continue;
        };
        let Some(kind) = obj.get("type").and_then(JsonValue::as_str) else {
            continue;
        };
        match kind {
            "file_citation" | "container_file_citation" | "file_path" => {
                if obj.get("file_id").and_then(JsonValue::as_str).is_some() {
                    out.push(item.clone());
                }
            }
            "url_citation" => {
                if obj.get("url").and_then(JsonValue::as_str).is_some() {
                    out.push(item.clone());
                }
            }
            _ => {}
        }
    }
    out
}

pub fn grounds_from_openai_citations(citations: &[JsonValue]) -> Vec<Ground> {
    let mut grounds = Vec::new();
    for citation in citations {
        let Some(ground_id) = extract_ground_id(citation) else {
            continue;
        };
        grounds.push(Ground {
            citation_key: ground_id.clone(),
            ground_id,
            role: LinkRole::Supports,
            creator: CreatorType::UpstreamPipeline,
            evidence_type: EvidenceType::Observation,
            evidence_content: Some("openai_citation".to_string()),
            signature: None,
        });
    }
    grounds
}

pub fn link_set_from_openai_citations(citations: &[JsonValue], statement_id: &str) -> LinkSet {
    let mut links = Vec::new();
    for (idx, citation) in citations.iter().enumerate() {
        let Some(ground_id) = extract_ground_id(citation) else {
            continue;
        };
        links.push(StatementGroundLink {
            statement_id: statement_id.to_string(),
            ground_id,
            role: LinkRole::Supports,
            provenance: Provenance {
                creator: CreatorType::UpstreamPipeline,
                evidence_type: EvidenceType::Observation,
                evidence_content: Some(format!("openai_citation[{idx}]")),
                signature: None,
            },
        });
    }
    LinkSet { links }
}

fn extract_ground_id(citation: &JsonValue) -> Option<String> {
    let obj = citation.as_object()?;
    let kind = obj.get("type")?.as_str()?;
    match kind {
        "file_citation" | "container_file_citation" | "file_path" => obj
            .get("file_id")
            .and_then(JsonValue::as_str)
            .map(ToString::to_string),
        "url_citation" => obj
            .get("url")
            .and_then(JsonValue::as_str)
            .map(ToString::to_string),
        _ => None,
    }
}

pub fn coerce_grounds_input(
    grounds_payload: Option<&[JsonValue]>,
    legacy_openai_citations: Option<&[JsonValue]>,
    _legacy_links: Option<&JsonValue>,
) -> Vec<Ground> {
    let mut normalized = Vec::new();

    if let Some(payload) = grounds_payload {
        let explicit = parse_grounds(payload);
        if !explicit.is_empty() {
            normalized.extend(explicit);
        } else {
            let typed = parse_openai_citations(payload);
            normalized.extend(grounds_from_openai_citations(&typed));
        }
    }

    if let Some(citations) = legacy_openai_citations {
        let typed = parse_openai_citations(citations);
        normalized.extend(grounds_from_openai_citations(&typed));
    }

    normalized
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::json::parse_json;

    #[test]
    fn extract_citation_keys_preserves_order() {
        let text = "First [@toolCall1], again [@toolCall1], then [@DocX].";
        assert_eq!(extract_citation_keys(text), vec!["toolCall1", "DocX"]);
    }

    #[test]
    fn build_links_only_for_cited_keys() {
        let grounds = vec![
            Ground {
                citation_key: "toolCall1".to_string(),
                ground_id: "issue_AGENT-8".to_string(),
                role: LinkRole::Supports,
                creator: CreatorType::UpstreamPipeline,
                evidence_type: EvidenceType::Observation,
                evidence_content: None,
                signature: None,
            },
            Ground {
                citation_key: "DocX".to_string(),
                ground_id: "file_123".to_string(),
                role: LinkRole::Supports,
                creator: CreatorType::UpstreamPipeline,
                evidence_type: EvidenceType::Observation,
                evidence_content: None,
                signature: None,
            },
        ];

        let links = build_links_from_grounds(
            "Need action [@toolCall1], nothing else.",
            &grounds,
            "final_response",
        );
        assert_eq!(links.links.len(), 1);
        assert_eq!(links.links[0].ground_id, "issue_AGENT-8");
    }

    #[test]
    fn parse_openai_citations_validates_payload() {
        let value =
            parse_json(r#"[{"type":"file_citation","file_id":"file_1","filename":"a","index":0}]"#)
                .expect("json parses");
        let JsonValue::Array(arr) = value else {
            panic!("array expected")
        };
        let out = parse_openai_citations(&arr);
        assert_eq!(out.len(), 1);
    }
}
