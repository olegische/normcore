use normcore::AdmissibilityStatus;
use normcore::ConversationMessage;
use normcore::CreatorType;
use normcore::EvaluateError;
use normcore::EvaluateInput;
use normcore::EvidenceType;
use normcore::Ground;
use normcore::JsonValue;
use normcore::LinkRole;
use normcore::ToolCall;
use normcore::evaluate;
use normcore::evaluate_from_json;
use normcore::parse_json;
use std::process::Command;

const COMPOSED_PAYLOAD: &str = r#"{
  "conversation": [
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "id":"callWeatherNYC",
          "type":"function",
          "function":{"name":"get_weather","arguments":"{\"city\":\"New York\"}"}
        }
      ]
    },
    {
      "role":"tool",
      "tool_call_id":"callWeatherNYC",
      "content":"{\"weather_id\":\"nyc_2026-02-07\"}"
    },
    {
      "role":"assistant",
      "content":"You should carry an umbrella [@callWeatherNYC] [@file_weather_2025]."
    }
  ],
  "grounds": [
    {"type":"file_citation","file_id":"file_weather_2025","filename":"weather.txt","index":0}
  ]
}"#;

fn composed_input() -> EvaluateInput {
    EvaluateInput {
        agent_output: None,
        conversation: Some(vec![
            ConversationMessage {
                role: "assistant".to_string(),
                content: Some(JsonValue::String(String::new())),
                tool_call_id: None,
                tool_calls: vec![ToolCall {
                    id: "callWeatherNYC".to_string(),
                    kind: "function".to_string(),
                    function_name: Some("get_weather".to_string()),
                    function_arguments: Some(JsonValue::String(
                        "{\"city\":\"New York\"}".to_string(),
                    )),
                    custom_name: None,
                    custom_input: None,
                }],
                function_name: None,
            },
            ConversationMessage {
                role: "tool".to_string(),
                content: Some(JsonValue::String(
                    "{\"weather_id\":\"nyc_2026-02-07\"}".to_string(),
                )),
                tool_call_id: Some("callWeatherNYC".to_string()),
                tool_calls: Vec::new(),
                function_name: None,
            },
            ConversationMessage {
                role: "assistant".to_string(),
                content: Some(JsonValue::String(
                    "You should carry an umbrella [@callWeatherNYC] [@file_weather_2025]."
                        .to_string(),
                )),
                tool_call_id: None,
                tool_calls: Vec::new(),
                function_name: None,
            },
        ]),
        grounds: Some(vec![Ground {
            citation_key: "file_weather_2025".to_string(),
            ground_id: "file_weather_2025".to_string(),
            role: LinkRole::Supports,
            creator: CreatorType::UpstreamPipeline,
            evidence_type: EvidenceType::Observation,
            evidence_content: Some("openai_citation".to_string()),
            signature: None,
        }]),
    }
}

fn run_cli(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_normcore"))
        .args(args)
        .output()
        .expect("normcore CLI must run in integration tests")
}

#[test]
fn boundary_cli_help_text_is_visible_without_arguments() {
    let output = run_cli(&[]);
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout).expect("CLI stdout must be UTF-8");
    assert!(stdout.contains("NormCore CLI."));
    assert!(stdout.contains("Usage:"));
}

#[test]
fn boundary_evaluate_from_json_rejects_invalid_field_shapes() {
    let conversation_err = evaluate_from_json(r#"{"agent_output":"x","conversation":{}}"#)
        .expect_err("conversation object must be rejected");
    assert_eq!(
        conversation_err,
        EvaluateError::InvalidJson("conversation must be an array".to_string())
    );

    let grounds_err = evaluate_from_json(r#"{"agent_output":"x","grounds":{}}"#)
        .expect_err("grounds object must be rejected");
    assert_eq!(
        grounds_err,
        EvaluateError::InvalidJson("grounds must be an array".to_string())
    );
}

#[test]
fn boundary_composed_pipeline_matches_between_typed_and_json_api() {
    let typed = evaluate(composed_input()).expect("typed API must evaluate composed input");
    let from_json = evaluate_from_json(COMPOSED_PAYLOAD).expect("JSON API must parse and evaluate");

    assert_eq!(from_json, typed);
    assert_eq!(from_json.status, AdmissibilityStatus::Acceptable);
    assert_eq!(from_json.grounds_accepted, 2);
    assert_eq!(from_json.grounds_cited, 2);
}

#[test]
fn boundary_cli_output_matches_library_contract() {
    let api = evaluate(EvaluateInput {
        agent_output: Some("We should deploy now.".to_string()),
        conversation: None,
        grounds: None,
    })
    .expect("library API must evaluate");

    let output = run_cli(&["evaluate", "--agent-output", "We should deploy now."]);
    assert!(
        output.status.success(),
        "CLI must succeed, stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let stdout = String::from_utf8(output.stdout).expect("CLI stdout must be UTF-8 JSON");
    let parsed = parse_json(&stdout).expect("CLI stdout must be valid JSON");
    let JsonValue::Object(obj) = parsed else {
        panic!("CLI output must be a JSON object")
    };
    let status = obj
        .get("status")
        .and_then(JsonValue::as_str)
        .expect("status string is required in CLI output");
    let licensed = match obj.get("licensed") {
        Some(JsonValue::Bool(v)) => *v,
        _ => panic!("licensed bool is required in CLI output"),
    };
    let can_retry = match obj.get("can_retry") {
        Some(JsonValue::Bool(v)) => *v,
        _ => panic!("can_retry bool is required in CLI output"),
    };

    assert_eq!(status, api.status.as_str());
    assert_eq!(licensed, api.licensed);
    assert_eq!(can_retry, api.can_retry);
}

#[test]
fn boundary_cli_rejects_non_array_conversation_argument() {
    let output = run_cli(&[
        "evaluate",
        "--conversation",
        r#"{"role":"assistant","content":"hello"}"#,
    ]);
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("--conversation must be JSON array"));
}

#[test]
fn boundary_cli_log_level_value_is_consumed_as_value_not_as_option() {
    let output = run_cli(&[
        "evaluate",
        "--log-level",
        "--agent-output",
        "--agent-output",
        "We should deploy now.",
    ]);
    assert!(
        output.status.success(),
        "CLI must succeed, stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let stdout = String::from_utf8(output.stdout).expect("CLI stdout must be UTF-8 JSON");
    let parsed = parse_json(&stdout).expect("CLI stdout must be valid JSON");
    let JsonValue::Object(obj) = parsed else {
        panic!("CLI output must be a JSON object")
    };
    let status = obj
        .get("status")
        .and_then(JsonValue::as_str)
        .expect("status string is required in CLI output");
    assert_eq!(status, "violates_norm");
}
