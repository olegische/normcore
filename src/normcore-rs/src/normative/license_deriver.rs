use crate::json::JsonValue;
use crate::models::LinkRole;
use crate::models::LinkSet;
use crate::models::StatementGroundLink;
use crate::normative::models::GroundSet;
use crate::normative::models::License;
use crate::normative::models::Modality;
use crate::normative::models::Scope;
use std::collections::BTreeSet;

pub struct LicenseDeriver;

impl LicenseDeriver {
    pub fn derive(&self, ground_set: &GroundSet, links: Option<&LinkSet>) -> License {
        match links {
            Some(link_set) => self.derive_with_links(ground_set, link_set),
            None => self.derive_conservative(ground_set),
        }
    }

    fn derive_conservative(&self, ground_set: &GroundSet) -> License {
        if ground_set.is_empty() {
            return license_from([Modality::Refusal]);
        }
        let factual_strength = ground_set.get_scope_strength(Scope::Factual);
        match factual_strength.as_deref() {
            None => license_from([Modality::Refusal]),
            Some("strong") => license_from([
                Modality::Assertive,
                Modality::Conditional,
                Modality::Refusal,
            ]),
            Some(_) => license_from([Modality::Conditional, Modality::Refusal]),
        }
    }

    fn derive_with_links(&self, ground_set: &GroundSet, links: &LinkSet) -> License {
        let support_links: Vec<&StatementGroundLink> = links
            .links
            .iter()
            .filter(|link| link.role == LinkRole::Supports)
            .collect();
        if support_links.is_empty() {
            return license_from([Modality::Refusal]);
        }

        let mut used = Vec::new();
        for link in support_links {
            if let Some(g) = ground_set.resolve_ground(&link.ground_id) {
                used.push(g);
            }
        }

        if used.is_empty() {
            return license_from([Modality::Refusal]);
        }

        let factual: Vec<_> = used
            .into_iter()
            .filter(|g| g.scope == Scope::Factual)
            .collect();
        if factual.is_empty() {
            return license_from([Modality::Refusal]);
        }

        if factual.iter().any(|g| g.strength == "strong") {
            return license_from([
                Modality::Assertive,
                Modality::Conditional,
                Modality::Refusal,
            ]);
        }

        license_from([Modality::Conditional, Modality::Refusal])
    }

    pub fn derive_with_trace(
        &self,
        ground_set: &GroundSet,
        links: Option<&LinkSet>,
    ) -> (License, JsonValue) {
        let license = self.derive(ground_set, links);
        let mut obj = std::collections::BTreeMap::new();
        obj.insert(
            "mode".to_string(),
            JsonValue::String(
                if links.is_some() {
                    "links"
                } else {
                    "conservative"
                }
                .to_string(),
            ),
        );
        obj.insert(
            "ground_set_size".to_string(),
            JsonValue::Number(ground_set.nodes.len() as f64),
        );
        obj.insert(
            "is_empty".to_string(),
            JsonValue::Bool(ground_set.is_empty()),
        );
        let mut factual = std::collections::BTreeMap::new();
        factual.insert(
            "present".to_string(),
            JsonValue::Bool(ground_set.has_scope(Scope::Factual)),
        );
        factual.insert(
            "strength".to_string(),
            match ground_set.get_scope_strength(Scope::Factual) {
                Some(v) => JsonValue::String(v),
                None => JsonValue::Null,
            },
        );
        factual.insert(
            "has_strong".to_string(),
            JsonValue::Bool(ground_set.has_strong_in_scope(Scope::Factual)),
        );
        obj.insert("factual".to_string(), JsonValue::Object(factual));
        obj.insert(
            "permitted_modalities".to_string(),
            JsonValue::Array(
                license
                    .permitted_modalities
                    .iter()
                    .map(|m| JsonValue::String(m.as_str().to_string()))
                    .collect(),
            ),
        );
        if let Some(linkset) = links {
            let supports_count = linkset
                .links
                .iter()
                .filter(|l| l.role == LinkRole::Supports)
                .count();
            obj.insert(
                "supports_links_count".to_string(),
                JsonValue::Number(supports_count as f64),
            );
        }

        (license, JsonValue::Object(obj))
    }
}

fn license_from<const N: usize>(modalities: [Modality; N]) -> License {
    let mut set = BTreeSet::new();
    for m in modalities {
        set.insert(m);
    }
    License {
        permitted_modalities: set,
    }
}
