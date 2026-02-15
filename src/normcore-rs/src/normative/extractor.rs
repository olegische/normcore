use crate::normative::models::Statement;

pub struct StatementExtractor;

impl StatementExtractor {
    pub fn extract(&self, text: &str) -> Vec<Statement> {
        if text.trim().is_empty() {
            return Vec::new();
        }
        let cleaned = self.strip_greeting(text);
        if cleaned.trim().is_empty() {
            return Vec::new();
        }
        vec![Statement {
            id: "final_response".to_string(),
            subject: "agent".to_string(),
            predicate: "participation".to_string(),
            raw_text: cleaned,
            modality: None,
            conditions: Vec::new(),
        }]
    }

    fn strip_greeting(&self, text: &str) -> String {
        let mut cleaned = text.trim().to_string();
        let lower = cleaned.to_lowercase();

        if !contains_any(
            &lower,
            &[
                "should",
                "must",
                "recommend",
                "prioritize",
                "block",
                "depends on",
                "is blocked",
                "is better",
                "better for you",
                "if ",
                "cannot determine",
                "not enough information",
                "i would not",
                "i won't",
                "for you",
                "given your",
                "based on your",
            ],
        ) {
            return String::new();
        }

        cleaned = self.strip_protocol_suffix(&cleaned);
        cleaned = self.strip_protocol_prefix_sentences(&cleaned);

        let prefixes = [
            "hello",
            "hi",
            "hey",
            "greetings",
            "good morning",
            "good afternoon",
            "good evening",
            "thanks for asking",
            "i'm doing well",
            "i am doing well",
            "i'm ready",
            "i am ready",
            "i'm here",
            "i am here",
            "hope you're doing well",
            "hope you are doing well",
        ];
        let lowered = cleaned.to_lowercase();
        for p in prefixes {
            if lowered.starts_with(p) {
                cleaned = cleaned[p.len()..]
                    .trim_start_matches(|c: char| c.is_whitespace() || ",.!-—".contains(c))
                    .to_string();
                break;
            }
        }

        if cleaned.trim_end().ends_with('?')
            && !contains_any(
                &cleaned.to_lowercase(),
                &["should", "must", "recommend", "if "],
            )
        {
            return String::new();
        }
        cleaned.trim().to_string()
    }

    fn strip_protocol_suffix(&self, text: &str) -> String {
        let mut out = text.trim().to_string();
        for _ in 0..5 {
            let lower = out.to_lowercase();
            let mut changed = false;
            for marker in [
                "i can help",
                "let me know if",
                "feel free to ask",
                "how can i help",
                "would you like",
            ] {
                if let Some(idx) = lower.rfind(marker) {
                    out = out[..idx]
                        .trim()
                        .trim_end_matches(&['.', ',', ';'][..])
                        .to_string();
                    changed = true;
                    break;
                }
            }
            if !changed {
                break;
            }
        }
        out
    }

    fn strip_protocol_prefix_sentences(&self, text: &str) -> String {
        let sentences = split_sentences(text);
        if sentences.is_empty() {
            return text.to_string();
        }
        let mut kept = Vec::new();
        for (idx, sentence) in sentences.iter().enumerate() {
            let lower = sentence.to_lowercase();
            let has_any_normative = contains_any(
                &lower,
                &[
                    "should",
                    "must",
                    "recommend",
                    "prioritize",
                    "blocks",
                    "is blocked",
                    "depends on",
                    "if ",
                    "for you",
                    "given your",
                    "based on your",
                    "i would not",
                    "cannot determine",
                ],
            );
            let has_strong_normative = contains_any(
                &lower,
                &[
                    "should",
                    "must",
                    "recommend",
                    "prioritize",
                    "blocks",
                    "depends on",
                    "if ",
                ],
            );
            let looks_protocol = contains_any(
                &lower,
                &[
                    "i can",
                    "how can i",
                    "what can i",
                    "thanks for",
                    "let me know",
                    "feel free",
                    "hope you",
                ],
            ) || (lower.trim().ends_with('?') && !has_any_normative);

            if looks_protocol && !has_strong_normative {
                continue;
            }
            if has_any_normative {
                for item in &sentences[idx..] {
                    kept.push(item.clone());
                }
                break;
            }
            kept.push(sentence.clone());
        }
        kept.join(" ").trim().to_string()
    }
}

fn split_sentences(text: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut buf = String::new();
    for c in text.chars() {
        buf.push(c);
        if matches!(c, '.' | '!' | '?') {
            let trimmed = buf.trim();
            if !trimmed.is_empty() {
                out.push(trimmed.to_string());
            }
            buf.clear();
        }
    }
    let tail = buf.trim();
    if !tail.is_empty() {
        out.push(tail.to_string());
    }
    out
}

fn contains_any(text: &str, needles: &[&str]) -> bool {
    needles.iter().any(|n| text.contains(n))
}
