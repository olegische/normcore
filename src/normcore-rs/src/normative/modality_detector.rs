use crate::normative::models::Modality;
use crate::normative::models::Statement;

pub struct ModalityDetector;

impl ModalityDetector {
    pub fn detect(&self, text: &str) -> Modality {
        let text_lower = text.to_lowercase();
        let core = self.extract_core_assertion(&text_lower);

        if self.is_refusal(&core) {
            return Modality::Refusal;
        }
        if self.is_goal_conditional(&core) {
            return Modality::Conditional;
        }
        if self.is_personalization_conditional(&core) {
            return Modality::Conditional;
        }
        if self.has_recommendation(&core) {
            return Modality::Assertive;
        }
        if self.is_conditional(&core) {
            return Modality::Conditional;
        }
        if self.is_descriptive(&core) && !self.is_normative(&core) {
            return Modality::Descriptive;
        }
        Modality::Assertive
    }

    pub fn detect_with_conditions(&self, statement: &mut Statement) {
        let modality = self.detect(&statement.raw_text);
        statement.modality = Some(modality.clone());
        if modality == Modality::Conditional {
            statement.conditions = self.extract_conditions(&statement.raw_text);
        }
    }

    fn is_refusal(&self, text: &str) -> bool {
        contains_any(
            text,
            &[
                "cannot determine",
                "cannot decide",
                "cannot choose",
                "need more",
                "require more",
                "insufficient",
                "please provide",
                "please clarify",
                "i don't know",
                "i do not know",
                "hard to say",
                "hard to determine",
                "i would not",
                "i won't",
            ],
        )
    }

    fn is_conditional(&self, text: &str) -> bool {
        contains_any(
            text,
            &[
                "if ",
                "unless ",
                "assuming ",
                "given that",
                "provided ",
                "depends on",
                " might ",
                " could ",
            ],
        )
    }

    fn is_goal_conditional(&self, text: &str) -> bool {
        text.starts_with("if your goal is")
            || text.starts_with("if you want")
            || text.starts_with("assuming you want")
            || text.starts_with("if you're optimizing")
            || text.starts_with("if you are optimizing")
            || text.starts_with("if you're aiming")
    }

    fn is_personalization_conditional(&self, text: &str) -> bool {
        contains_any(
            text,
            &[
                "for you",
                "given your",
                "based on your",
                "according to your",
                "with your preferences",
                "with your constraints",
            ],
        )
    }

    fn is_descriptive(&self, text: &str) -> bool {
        contains_any(
            text,
            &[
                "blocks",
                "is blocked by",
                "depends on",
                "has status",
                "due date is",
                "is blocked",
            ],
        )
    }

    fn is_normative(&self, text: &str) -> bool {
        contains_any(
            text,
            &[
                "should",
                "must",
                "need to",
                "needs to",
                "recommend",
                "suggest",
                "advise",
            ],
        )
    }

    fn has_recommendation(&self, text: &str) -> bool {
        contains_any(
            text,
            &[
                " is better",
                " are better",
                "should be prioritiz",
                "recommend ",
                "suggest you",
                "best choice",
                "best option",
                "prioritize ",
                " first",
            ],
        )
    }

    fn extract_core_assertion(&self, text: &str) -> String {
        if let Some((core, _)) = text.split_once("\n\n") {
            return core.trim().to_string();
        }
        if let Some(idx) = text.find(". ") {
            return text[..=idx].trim().to_string();
        }
        if let Some((core, _)) = text.split_once('\n') {
            return core.trim().to_string();
        }
        text.chars()
            .take(500)
            .collect::<String>()
            .trim()
            .to_string()
    }

    fn extract_conditions(&self, text: &str) -> Vec<String> {
        let lower = text.to_lowercase();
        let mut out = Vec::new();

        if let Some(c) = extract_after_keyword(&lower, "if ") {
            out.push(c);
        }
        if let Some(c) = extract_after_keyword(&lower, "unless ") {
            out.push(format!("NOT {c}"));
        }
        if let Some(c) = extract_after_keyword(&lower, "assuming ") {
            out.push(c);
        }
        if let Some(c) = extract_after_keyword(&lower, "given that ") {
            out.push(c);
        }
        if let Some(c) = extract_after_keyword(&lower, "given your ") {
            out.push(format!("given your {c}"));
        }
        if let Some(c) = extract_after_keyword(&lower, "based on your ") {
            out.push(format!("based on your {c}"));
        }
        if lower.contains("for you") {
            out.push("for you".to_string());
        }

        if out.is_empty() {
            out.push("unspecified".to_string());
        }
        out
    }
}

fn extract_after_keyword(text: &str, keyword: &str) -> Option<String> {
    let start = text.find(keyword)? + keyword.len();
    let tail = &text[start..];
    let end = tail
        .find(|c: char| [',', '.', ';'].contains(&c))
        .unwrap_or(tail.len());
    let clause = tail[..end].trim();
    if clause.is_empty() {
        None
    } else {
        Some(clause.to_string())
    }
}

fn contains_any(text: &str, needles: &[&str]) -> bool {
    needles.iter().any(|n| text.contains(n))
}
