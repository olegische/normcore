use normcore_rs::AdmissibilityStatus;
use normcore_rs::ConversationMessage;
use normcore_rs::CreatorType;
use normcore_rs::EvaluateInput;
use normcore_rs::EvidenceType;
use normcore_rs::Ground;
use normcore_rs::JsonValue;
use normcore_rs::LinkRole;
use normcore_rs::ToolCall;
use normcore_rs::evaluate;

fn assistant_text(content: &str) -> ConversationMessage {
    ConversationMessage {
        role: "assistant".to_string(),
        content: Some(JsonValue::String(content.to_string())),
        tool_call_id: None,
        tool_calls: Vec::new(),
        function_name: None,
    }
}

#[test]
fn scenario_conversation_with_tool_citation_produces_grounded_acceptable_status() {
    // Arrange
    let conversation = vec![
        ConversationMessage {
            role: "assistant".to_string(),
            content: Some(JsonValue::String(String::new())),
            tool_call_id: None,
            tool_calls: vec![ToolCall {
                id: "callWeatherNYC".to_string(),
                kind: "function".to_string(),
                function_name: Some("get_weather".to_string()),
                function_arguments: Some(JsonValue::String("{\"city\":\"New York\"}".to_string())),
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
        assistant_text("You should carry an umbrella [@callWeatherNYC]."),
    ];

    // Act
    let judgment = evaluate(EvaluateInput {
        agent_output: None,
        conversation: Some(conversation),
        grounds: None,
    })
    .expect("evaluation should succeed");

    // Assert
    assert_eq!(judgment.status, AdmissibilityStatus::Acceptable);
    assert!(judgment.licensed);
    assert!(!judgment.can_retry);
    assert_eq!(judgment.grounds_accepted, 1);
    assert_eq!(judgment.grounds_cited, 1);
    assert_eq!(judgment.num_statements, 1);
    assert_eq!(judgment.statement_evaluations.len(), 1);
}

#[test]
fn scenario_external_ground_without_tool_history_keeps_assertive_claim_acceptable() {
    // Arrange
    let grounds = vec![Ground {
        citation_key: "file_weather_2025".to_string(),
        ground_id: "file_weather_2025".to_string(),
        role: LinkRole::Supports,
        creator: CreatorType::UpstreamPipeline,
        evidence_type: EvidenceType::Observation,
        evidence_content: Some("openai_citation".to_string()),
        signature: None,
    }];

    // Act
    let judgment = evaluate(EvaluateInput {
        agent_output: Some("You should compare with archive [@file_weather_2025].".to_string()),
        conversation: None,
        grounds: Some(grounds),
    })
    .expect("evaluation should succeed");

    // Assert
    assert_eq!(judgment.status, AdmissibilityStatus::Acceptable);
    assert_eq!(judgment.grounds_accepted, 1);
    assert_eq!(judgment.grounds_cited, 1);
    assert_eq!(judgment.violated_axioms, Vec::<String>::new());
}

#[test]
fn scenario_assertive_without_grounding_returns_norm_violation() {
    // Arrange / Act
    let judgment = evaluate(EvaluateInput {
        agent_output: Some("We should deploy now.".to_string()),
        conversation: None,
        grounds: None,
    })
    .expect("evaluation should succeed");

    // Assert
    assert_eq!(judgment.status, AdmissibilityStatus::ViolatesNorm);
    assert!(!judgment.licensed);
    assert!(judgment.can_retry);
    assert_eq!(judgment.violated_axioms, vec!["A5".to_string()]);
    assert_eq!(judgment.grounds_accepted, 0);
    assert_eq!(judgment.grounds_cited, 0);
}
