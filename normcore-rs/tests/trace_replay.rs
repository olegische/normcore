use normcore::ConversationMessage;
use normcore::EvaluateInput;
use normcore::Ground;
use normcore::JsonValue;
use normcore::coerce_grounds_input;
use normcore::evaluate;
use normcore::parse_conversation;
use normcore::parse_json;
use std::collections::BTreeMap;
use std::path::PathBuf;

#[derive(Debug)]
struct Trace {
    name: String,
    steps: Vec<TraceStep>,
}

#[derive(Debug)]
struct TraceStep {
    event: String,
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
    num_statements: usize,
    violated_axioms: Vec<String>,
    grounds_accepted_at_least: Option<usize>,
    grounds_cited_at_least: Option<usize>,
}

#[test]
fn replay_formal_traces() {
    let traces = load_traces();
    assert!(!traces.is_empty(), "trace fixture must not be empty");
    run_traces(&traces);
}

#[test]
fn replay_generated_formal_trace() {
    let Some(path) = std::env::var_os("TRACE_REPLAY_JSON") else {
        return;
    };
    let raw = std::fs::read_to_string(&path)
        .unwrap_or_else(|err| panic!("failed to read TRACE_REPLAY_JSON {path:?}: {err}"));
    let root = parse_json(&raw).expect("generated trace JSON must parse");
    let root_obj = as_object(&root);
    let steps = as_array(required_field(root_obj, "steps"))
        .iter()
        .map(parse_generated_step)
        .collect::<Vec<_>>();
    let trace = Trace {
        name: format!("generated:{}", PathBuf::from(path).display()),
        steps,
    };
    run_traces(&[trace]);
}

fn run_traces(traces: &[Trace]) {
    for trace in traces {
        for (idx, step) in trace.steps.iter().enumerate() {
            let result = evaluate(EvaluateInput {
                agent_output: step.agent_output.clone(),
                conversation: step.conversation.clone(),
                grounds: step.grounds.clone(),
            })
            .unwrap_or_else(|err| {
                panic!(
                    "trace '{}' step {} ({}) failed: {err:?}",
                    trace.name, idx, step.event
                )
            });

            let prefix = format!("trace '{}' step {} ({})", trace.name, idx, step.event);
            assert_eq!(
                result.status.as_str(),
                step.expect.status,
                "{prefix}: status mismatch"
            );
            assert_eq!(
                result.licensed, step.expect.licensed,
                "{prefix}: licensed mismatch"
            );
            assert_eq!(
                result.can_retry, step.expect.can_retry,
                "{prefix}: can_retry mismatch"
            );
            assert_eq!(
                result.num_statements, step.expect.num_statements,
                "{prefix}: num_statements mismatch"
            );
            assert_eq!(
                result.violated_axioms, step.expect.violated_axioms,
                "{prefix}: violated_axioms mismatch"
            );

            if let Some(min) = step.expect.grounds_accepted_at_least {
                assert!(
                    result.grounds_accepted >= min,
                    "{prefix}: grounds_accepted too small (got {}, min {})",
                    result.grounds_accepted,
                    min
                );
            }
            if let Some(min) = step.expect.grounds_cited_at_least {
                assert!(
                    result.grounds_cited >= min,
                    "{prefix}: grounds_cited too small (got {}, min {})",
                    result.grounds_cited,
                    min
                );
            }
        }
    }
}

fn load_traces() -> Vec<Trace> {
    let root = parse_json(include_str!("fixtures/trace_replay.json")).expect("fixture must parse");
    let root_obj = as_object(&root);
    let traces = as_array(required_field(root_obj, "traces"));
    traces.iter().map(parse_trace).collect()
}

fn parse_trace(value: &JsonValue) -> Trace {
    let obj = as_object(value);
    let name = required_string(obj, "name").to_string();
    let steps = as_array(required_field(obj, "steps"))
        .iter()
        .map(parse_step)
        .collect();
    Trace { name, steps }
}

fn parse_generated_step(value: &JsonValue) -> TraceStep {
    let obj = as_object(value);
    let event = required_string(obj, "op").to_string();
    let args_obj = as_object(required_field(obj, "args"));
    let expect = parse_expected(as_object(required_field(obj, "expect")), &event);

    let agent_output = match args_obj.get("agent_output") {
        Some(JsonValue::String(s)) => Some(s.clone()),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("event '{event}' has invalid generated args.agent_output"),
    };

    let conversation = match args_obj.get("conversation") {
        Some(JsonValue::Array(items)) => Some(parse_conversation(items).unwrap_or_else(|err| {
            panic!("event '{event}' has invalid generated conversation: {err:?}")
        })),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("event '{event}' has invalid generated conversation"),
    };

    let grounds = match args_obj.get("grounds") {
        Some(JsonValue::Array(items)) => Some(coerce_grounds_input(Some(items), None, None)),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("event '{event}' has invalid generated grounds"),
    };

    TraceStep {
        event,
        agent_output,
        conversation,
        grounds,
        expect,
    }
}

fn parse_step(value: &JsonValue) -> TraceStep {
    let obj = as_object(value);
    let event = required_string(obj, "event").to_string();

    let agent_output = match obj.get("agent_output") {
        Some(JsonValue::String(s)) => Some(s.clone()),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("event '{event}' has invalid agent_output"),
    };

    let conversation = match obj.get("conversation") {
        Some(JsonValue::Array(items)) => Some(
            parse_conversation(items)
                .unwrap_or_else(|err| panic!("event '{event}' has invalid conversation: {err:?}")),
        ),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("event '{event}' has invalid conversation"),
    };

    let grounds = match obj.get("grounds") {
        Some(JsonValue::Array(items)) => Some(coerce_grounds_input(Some(items), None, None)),
        Some(JsonValue::Null) | None => None,
        Some(_) => panic!("event '{event}' has invalid grounds"),
    };

    let expect = parse_expected(as_object(required_field(obj, "expect")), &event);

    TraceStep {
        event,
        agent_output,
        conversation,
        grounds,
        expect,
    }
}

fn parse_expected(expect_obj: &BTreeMap<String, JsonValue>, event: &str) -> Expected {
    let status = required_string(expect_obj, "status").to_string();
    let licensed = required_bool(expect_obj, "licensed");
    let can_retry = required_bool(expect_obj, "can_retry");
    let num_statements = required_usize(expect_obj, "num_statements");

    let violated_axioms = match expect_obj.get("violated_axioms") {
        Some(JsonValue::Array(values)) => values
            .iter()
            .map(|v| match v {
                JsonValue::String(s) => s.clone(),
                _ => panic!("event '{event}' has non-string violated_axioms"),
            })
            .collect(),
        Some(_) => panic!("event '{event}' has invalid violated_axioms"),
        None => Vec::new(),
    };

    let grounds_accepted_at_least = optional_usize(expect_obj, "grounds_accepted_at_least");
    let grounds_cited_at_least = optional_usize(expect_obj, "grounds_cited_at_least");

    Expected {
        status,
        licensed,
        can_retry,
        num_statements,
        violated_axioms,
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
