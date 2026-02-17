use normcore_rs::AdmissibilityStatus;
use normcore_rs::EvaluateInput;
use normcore_rs::JsonValue;
use normcore_rs::evaluate;
use normcore_rs::evaluate_from_json;
use normcore_rs::extract_citation_keys;
use normcore_rs::to_pretty_json;
use proptest::prelude::*;
use proptest::string::string_regex;
use std::collections::HashSet;

fn assert_status_contract(status: &AdmissibilityStatus, licensed: bool, can_retry: bool) {
    match status {
        AdmissibilityStatus::Acceptable | AdmissibilityStatus::ConditionallyAcceptable => {
            assert!(licensed);
            assert!(!can_retry);
        }
        AdmissibilityStatus::ViolatesNorm | AdmissibilityStatus::IllFormed => {
            assert!(!licensed);
            assert!(can_retry);
        }
        AdmissibilityStatus::Unsupported => {
            assert!(licensed);
            assert!(can_retry);
        }
        AdmissibilityStatus::Underdetermined | AdmissibilityStatus::NoNormativeContent => {
            assert!(!licensed);
            assert!(!can_retry);
        }
    }
}

proptest! {
    #[test]
    fn prop_evaluate_is_deterministic(agent_output in ".{0,160}") {
        let input = EvaluateInput {
            agent_output: Some(agent_output.clone()),
            conversation: None,
            grounds: None,
        };

        let first = evaluate(input.clone()).expect("evaluation must succeed");
        let second = evaluate(input).expect("evaluation must succeed");

        prop_assert_eq!(first, second);
    }

    #[test]
    fn prop_status_contract_holds(agent_output in ".{0,160}") {
        let result = evaluate(EvaluateInput {
            agent_output: Some(agent_output),
            conversation: None,
            grounds: None,
        }).expect("evaluation must succeed");

        assert_status_contract(&result.status, result.licensed, result.can_retry);
        prop_assert!(result.grounds_cited <= result.grounds_accepted);
        prop_assert!(result.num_acceptable <= result.num_statements);
        prop_assert_eq!(result.statement_evaluations.len(), result.num_statements);
    }

    #[test]
    fn prop_json_api_matches_direct(agent_output in ".{0,160}") {
        let escaped = to_pretty_json(&JsonValue::String(agent_output.clone()));
        let payload = format!("{{\"agent_output\":{escaped}}}");

        let from_json = evaluate_from_json(&payload).expect("JSON API must succeed");
        let direct = evaluate(EvaluateInput {
            agent_output: Some(agent_output),
            conversation: None,
            grounds: None,
        }).expect("direct API must succeed");

        prop_assert_eq!(from_json, direct);
    }

    #[test]
    fn prop_extract_citation_keys_is_ordered_and_unique(
        keys in proptest::collection::vec(string_regex("[A-Za-z][A-Za-z0-9_-]{0,12}").expect("regex"), 0..30)
    ) {
        let mut text = String::new();
        let mut encountered = Vec::new();

        for (idx, key) in keys.iter().enumerate() {
            if idx % 3 == 0 {
                text.push_str(&format!("preface [@{key}] "));
                encountered.push(key.clone());
            }
            text.push_str(&format!("again [@{key}] "));
            encountered.push(key.clone());
        }

        let mut seen = HashSet::new();
        let mut expected = Vec::new();
        for key in encountered {
            if seen.insert(key.clone()) {
                expected.push(key);
            }
        }

        let actual = extract_citation_keys(&text);
        prop_assert_eq!(actual, expected);
    }
}
