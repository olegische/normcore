use normcore_rs::ConversationMessage;
use normcore_rs::EvaluateInput;
use normcore_rs::Ground;
use normcore_rs::JsonValue;
use normcore_rs::coerce_grounds_input;
use normcore_rs::evaluate;
use normcore_rs::parse_conversation;
use normcore_rs::parse_json;
use std::collections::BTreeMap;

#[derive(Debug)]
struct GoldenCase {
    name: String,
    agent_output: Option<String>,
    conversation: Option<Vec<ConversationMessage>>,
    grounds: Option<Vec<Ground>>,
    expect: Expected,
}

#[derive(Debug)]
struct Expected {
    status: String,
    licensed: bool,
    can_retry: bool,
    violated_axioms: Vec<String>,
    num_statements: usize,
    grounds_accepted_at_least: Option<usize>,
    grounds_cited_at_least: Option<usize>,
}

#[test]
fn golden_corpus_regression() {
    let cases = load_cases();
    assert!(!cases.is_empty(), "golden corpus must not be empty");

    for case in cases {
        let result = evaluate(EvaluateInput {
            agent_output: case.agent_output.clone(),
            conversation: case.conversation.clone(),
            grounds: case.grounds.clone(),
        })
        .unwrap_or_else(|err| panic!("case '{}' failed to evaluate: {err:?}", case.name));

        assert_eq!(
            result.status.as_str(),
            case.expect.status,
            "status mismatch for case {}",
            case.name
        );
        assert_eq!(
            result.licensed, case.expect.licensed,
            "licensed mismatch for case {}",
            case.name
        );
        assert_eq!(
            result.can_retry, case.expect.can_retry,
            "can_retry mismatch for case {}",
            case.name
        );
        assert_eq!(
            result.violated_axioms, case.expect.violated_axioms,
            "violated axioms mismatch for case {}",
            case.name
        );
        assert_eq!(
            result.num_statements, case.expect.num_statements,
            "num_statements mismatch for case {}",
            case.name
        );

        if let Some(min) = case.expect.grounds_accepted_at_least {
            assert!(
                result.grounds_accepted >= min,
                "grounds_accepted too small for case {} (got {}, min {})",
                case.name,
                result.grounds_accepted,
                min
            );
        }
        if let Some(min) = case.expect.grounds_cited_at_least {
            assert!(
                result.grounds_cited >= min,
                "grounds_cited too small for case {} (got {}, min {})",
                case.name,
                result.grounds_cited,
                min
            );
        }
    }
}

fn load_cases() -> Vec<GoldenCase> {
    let root = parse_json(include_str!("fixtures/golden_corpus.json")).expect("fixture must parse");
    let root_obj = as_object(&root);
    let entries = as_array(required_field(root_obj, "cases"));

    entries.iter().map(parse_case).collect()
}

fn parse_case(value: &JsonValue) -> GoldenCase {
    let obj = as_object(value);
    let name = required_string(obj, "name").to_string();

    let agent_output = match obj.get("agent_output") {
        Some(JsonValue::String(s)) => Some(s.clone()),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("case '{name}' has invalid agent_output"),
    };

    let conversation = match obj.get("conversation") {
        Some(JsonValue::Array(items)) => Some(
            parse_conversation(items)
                .unwrap_or_else(|err| panic!("case '{name}' has invalid conversation: {err:?}")),
        ),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("case '{name}' has invalid conversation value"),
    };

    let grounds = match obj.get("grounds") {
        Some(JsonValue::Array(items)) => Some(coerce_grounds_input(Some(items), None, None)),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("case '{name}' has invalid grounds value"),
    };

    let expect = parse_expected(as_object(required_field(obj, "expect")), &name);

    GoldenCase {
        name,
        agent_output,
        conversation,
        grounds,
        expect,
    }
}

fn parse_expected(expect_obj: &BTreeMap<String, JsonValue>, case_name: &str) -> Expected {
    let status = required_string(expect_obj, "status").to_string();
    let licensed = required_bool(expect_obj, "licensed");
    let can_retry = required_bool(expect_obj, "can_retry");
    let num_statements = required_usize(expect_obj, "num_statements");

    let violated_axioms = match expect_obj.get("violated_axioms") {
        Some(JsonValue::Array(values)) => values
            .iter()
            .map(|v| match v {
                JsonValue::String(s) => s.clone(),
                _ => panic!("case '{case_name}' has non-string violated_axioms entry"),
            })
            .collect(),
        Some(_) => panic!("case '{case_name}' has invalid violated_axioms"),
        None => Vec::new(),
    };

    let grounds_accepted_at_least = optional_usize(expect_obj, "grounds_accepted_at_least");
    let grounds_cited_at_least = optional_usize(expect_obj, "grounds_cited_at_least");

    Expected {
        status,
        licensed,
        can_retry,
        violated_axioms,
        num_statements,
        grounds_accepted_at_least,
        grounds_cited_at_least,
    }
}

fn required_field<'a>(obj: &'a BTreeMap<String, JsonValue>, key: &str) -> &'a JsonValue {
    obj.get(key)
        .unwrap_or_else(|| panic!("missing required field '{key}'"))
}

fn as_object(value: &JsonValue) -> &BTreeMap<String, JsonValue> {
    value.as_object().expect("JSON object expected in fixture")
}

fn as_array(value: &JsonValue) -> &[JsonValue] {
    value.as_array().expect("JSON array expected in fixture")
}

fn required_string<'a>(obj: &'a BTreeMap<String, JsonValue>, key: &str) -> &'a str {
    required_field(obj, key)
        .as_str()
        .unwrap_or_else(|| panic!("field '{key}' must be string"))
}

fn required_bool(obj: &BTreeMap<String, JsonValue>, key: &str) -> bool {
    match required_field(obj, key) {
        JsonValue::Bool(v) => *v,
        _ => panic!("field '{key}' must be bool"),
    }
}

fn required_usize(obj: &BTreeMap<String, JsonValue>, key: &str) -> usize {
    match required_field(obj, key) {
        JsonValue::Number(v) if *v >= 0.0 => *v as usize,
        _ => panic!("field '{key}' must be non-negative number"),
    }
}

fn optional_usize(obj: &BTreeMap<String, JsonValue>, key: &str) -> Option<usize> {
    match obj.get(key) {
        Some(JsonValue::Number(v)) if *v >= 0.0 => Some(*v as usize),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("field '{key}' must be non-negative number when present"),
    }
}
