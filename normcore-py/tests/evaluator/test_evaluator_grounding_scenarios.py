from normcore import evaluate


def test_tool_conversation_populates_grounding_trace():
    conversation = [
        {
            "role": "user",
            "content": "What is the weather in New York and what should I do?",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "callWeatherNYC",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city":"New York","units":"metric"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "callWeatherNYC",
            "content": (
                '{"weather_id":"nyc_2026-02-07","city":"New York",'
                '"condition":"rain","temperature_c":4}'
            ),
        },
        {
            "role": "assistant",
            "content": "You should carry an umbrella in New York today [@callWeatherNYC].",
        },
    ]

    judgment = evaluate(conversation=conversation)

    assert judgment.statement_evaluations
    assert len(judgment.statement_evaluations[0].grounding_trace) > 0


def test_external_grounds_are_included_with_tool_grounds():
    conversation = [
        {
            "role": "system",
            "content": (
                "RAG_CONTEXT file_weather_archive_2025: On 2025-02-07 in New York, "
                "condition=snow, temperature_c=-1, source=weather_archive_file."
            ),
        },
        {
            "role": "user",
            "content": "What is the weather in New York today, and how does it compare to last year?",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "callWeatherNYC",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city":"New York","units":"metric"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "callWeatherNYC",
            "content": (
                '{"weather_id":"nyc_2026-02-07","city":"New York",'
                '"condition":"rain","temperature_c":4}'
            ),
        },
        {
            "role": "assistant",
            "content": (
                "It is warmer and rainy in New York today compared to one year ago, "
                "so you should carry an umbrella [@callWeatherNYC] "
                "[@file_weather_archive_2025]."
            ),
        },
    ]
    grounds = [
        {
            "citation_key": "file_weather_archive_2025",
            "ground_id": "file_weather_archive_2025",
        }
    ]

    judgment = evaluate(conversation=conversation, grounds=grounds)

    assert judgment.statement_evaluations
    trace = judgment.statement_evaluations[0].grounding_trace
    semantic_ids = {item.semantic_id for item in trace}

    assert len(trace) >= 2
    assert "file_weather_archive_2025" in semantic_ids
